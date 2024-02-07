# coding: utf-8
# DRONE VISION v1 
# Author : Antoine GOUEDARD
# edited by @jasperan to modify original functionality

import argparse
import datetime
import itertools
import sys
import oci
import json
import os
import base64
import cv2
import numpy as np
import time
import threading
import subprocess as sp
import logging 
from PIL import Image
import shutil
import moviepy.video.io.ImageSequenceClip
from natsort import natsorted


parser = argparse.ArgumentParser(description='Process video file.')
parser.add_argument('--file', type=str,
                    default='H:/Downloads/tratraffic.mp4',
                    help='Path to the video file'
)
args = parser.parse_args()
file_dir = args.file

###################################################################################################
# Variables
###################################################################################################
desired_fps = 30

# Specify the command to execute (fpvliberator will get data from usb, create the stdout binary stream, send it to ffmpeg that will analyze the stream and allow python to extract frames from it)
cmd_to_execute = """./fpvLiberator| ffmpeg -i pipe: -f rawvideo -pix_fmt bgr24 -an -sn pipe:"""
# Directory path of the fpvLiberator exec
dir_path = "H:/Downloads/"
# Output Video File name and Location
file_to_write = '/H:/Downloads/'+ str(datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S"))+'.avi'
# Maximum number of potential objects to detect per frame
max_objects_to_detect_per_frame = 20
# Quality of the frames (png) to send to the API (to reduce latency)
percent_of_original_size = 50
# Sleep interval between attempts to retrieve the next frame to write in the Output Video File
sleep_interval = 0.2
# Max waiting time before giving up the next frame to write in the Output Video File (in seconds)
max_wait_time = 3.9
# Specific things to recognize; format : "name" , "object name in OCI AI VIsion", "b" : "blue color", "g" ; "green color", "r" : "red color"
items_to_highlight = [
    {"name": "Person", "b": "0", "g" : "255", "r":"0"},
    {"name": "Tree", "b": "255", "g" : "255", "r":"0"},
    {"name": "Drone", "b": "0", "g" : "255", "r":"0"}, 
    {"name": "Machine", "b": "0", "g" : "255", "r":"0"}, 
    {"name": "Stone", "b": "0", "g" : "0", "r":"255"}, 
    {"name": "Rock", "b": "0", "g" : "0", "r":"255"}]
# Specific things to notify, format : "name" , "object name in OCI AI VIsion", "message" : "message in email/SMS/etc.."
'''
items_to_notify = [
    {"name": "Rifle", "message": "Alert ! Someone holding a gun has been detected, please send immediately a police squad at location (X)"},
    {"name": "Handgun", "message": "Alert ! Someone holding a gun has been detected, please send immediately a police squad at location (X)"},
    {"name": "Knife", "message": "Alert ! Someone holding a knife has been detected, please send immediately a police squad at location (X)"}
]
'''

items_to_notify = []

# OCI notification Service Topic ID
#
# OCI_topic_id ="ocid1.onstopic.oc1.eu-frankfurt-1."

###################################################################################################
# Print header centered
###################################################################################################
def print_header(name):
    chars = int(90)
    print("")
    print('#' * chars)
    print("#" + name.center(chars - 2, " ") + "#")
    print('#' * chars)

###################################################################################################
# check service error to warn instead of error
###################################################################################################
def check_service_error(code):
    return ('max retries exceeded' in str(code).lower() or
            'auth' in str(code).lower() or
            'notfound' in str(code).lower() or
            code == 'Forbidden' or
            code == 'TooManyRequests' or
            code == 'IncorrectState' or
            code == 'LimitExceeded'
            )

###################################################################################################
# Create signer for Authentication
# Input - config_profile and is_instance_principals and is_delegation_token
# Output - config and signer objects
###################################################################################################
def create_signer(config_profile, is_instance_principals, is_delegation_token):

    # if instance principals authentications
    if is_instance_principals:
        try:
            signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
            config = {'region': signer.region, 'tenancy': signer.tenancy_id}
            return config, signer

        except Exception:
            print_header("Error obtaining instance principals certificate, aborting")
            raise SystemExit

    # -----------------------------
    # Delegation Token
    # -----------------------------
    elif is_delegation_token:

        try:
            # check if env variables OCI_CONFIG_FILE, OCI_CONFIG_PROFILE exist and use them
            env_config_file = os.environ.get('OCI_CONFIG_FILE')
            env_config_section = os.environ.get('OCI_CONFIG_PROFILE')

            # check if file exist
            if env_config_file is None or env_config_section is None:
                print("*** OCI_CONFIG_FILE and OCI_CONFIG_PROFILE env variables not found, abort. ***")
                raise SystemExit

            config = oci.config.from_file(env_config_file, env_config_section)
            delegation_token_location = config["delegation_token_file"]

            with open(delegation_token_location, 'r') as delegation_token_file:
                delegation_token = delegation_token_file.read().strip()
                # get signer from delegation token
                signer = oci.auth.signers.InstancePrincipalsDelegationTokenSigner(delegation_token=delegation_token)

                return config, signer

        except KeyError:
            print("* Key Error obtaining delegation_token_file")
            raise SystemExit

        except Exception:
            raise

    # -----------------------------
    # config file authentication
    # -----------------------------
    # else:
    #     config = oci.config.from_file(
    #         oci.config.DEFAULT_LOCATION,
    #         (config_profile if config_profile else oci.config.DEFAULT_PROFILE)
    #     )
    else:
        config = oci.config.from_file(
             oci.config.DEFAULT_LOCATION,
             (config_profile if config_profile else oci.config.DEFAULT_PROFILE),
        )
        signer = oci.signer.Signer(
            tenancy=config["tenancy"],
            user=config["user"],
            fingerprint=config["fingerprint"],
            private_key_file_location=config.get("key_file"),
            pass_phrase=oci.config.get_config_value_or_default(config, "pass_phrase"),
            private_key_content=config.get("key_content")
        )
        return config, signer

###################################################################################################
# Draws the box around objects  / recognize their types  / send notifications 
###################################################################################################
def draw_object_info(image_objects, img):
    for image_object in image_objects:
        width = img.shape[1]
        height = img.shape[0]
        vertices = image_object["bounding_polygon"]["normalized_vertices"]
        vertex_x = vertices[0]['x'] * width
        vertex_y = vertices[0]['y'] * height
        box_width = (vertices[2]['x'] - vertices[0]['x']) * width
        box_height = (vertices[2]['y'] - vertices[0]['y']) * height
        start_point = (int(vertex_x), int(vertex_y + box_height))
        end_point = (int(vertex_x + box_width), int(vertex_y))
        highlight_item = next(filter(lambda item: item["name"] == image_object["name"], items_to_highlight), None)
        if highlight_item is not None:
            color=(int(highlight_item["b"]),int(highlight_item["g"]),int(highlight_item["r"]))
            thickness = 2
            police_size = 1.25
            police_thickness = 3
        else :
            color = (255, 255, 255)
            thickness = 1
            police_size = 1
            police_thickness = 1
        item_to_notify = next(filter(lambda item: item["name"] == image_object["name"], items_to_notify), None)
        if item_to_notify is not None:
            if item_to_notify["name"] not in items_notified:
                # sending an alert
                #publish_message_response = ons_client.publish_message(
                #    topic_id=OCI_topic_id,
                #    message_details=oci.ons.models.MessageDetails(
                #        body=item_to_notify["message"],
                #        title="Alert ! : "+item_to_notify["name"]+" has been found"))
                #items_notified.append(item_to_notify["name"])
                #logger.debug(publish_message_response.data)
                pass
        cv2.rectangle(img, start_point, end_point, color, thickness)
        cv2.putText(img, image_object["name"], (int(vertex_x + 15), int(vertex_y + box_height + 30)), cv2.FONT_HERSHEY_SIMPLEX, police_size, color, police_thickness, 2)

###################################################################################################
# Analyze image / call to API OCI AI VISION / create a new augmented image
###################################################################################################
def analyzeImage(img,frame_number,length,dict,lock):
    time_request_elapsed = time.time()
    scale_percent = percent_of_original_size
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    img_resized = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    _, im_arr = cv2.imencode('.png',img_resized)
    im_bytes = im_arr.tobytes()
    im_b64 = base64.b64encode(im_bytes)
    image_data = im_b64.decode('utf-8')   
    image_details = oci.ai_vision.models.InlineImageDetails(data=image_data)
    analysis_job = ai_vision_client.analyze_image(
    analyze_image_details=oci.ai_vision.models.AnalyzeImageDetails(
        features=[
            oci.ai_vision.models.ImageClassificationFeature(
                feature_type="OBJECT_DETECTION",
                max_results=max_objects_to_detect_per_frame)
                ],
        image=image_details
    ))
    res_json = json.loads(repr(analysis_job.data)) 
    time_request_elapsed = time.time() - time_request_elapsed
    logger.debug("Call OCI AI Vision API took :"  + str(time_request_elapsed)+ " for frame "+str(frame_number))
    if res_json["image_objects"] is not None:
        drawing_canvas = np.zeros(img.shape[:3], dtype="uint8")
        draw_object_info(res_json["image_objects"], drawing_canvas)
        img_augmented = cv2.bitwise_or(drawing_canvas, img)
        #cv2.imshow('outputto', img_augmented)
        #key = cv2.waitKey(3000)#pauses for 3 seconds before fetching next image
        #if key == 27:#if ESC is pressed, exit loop
        #    cv2.destroyAllWindows()
        #print('Obtained Image with {}'.format())
        lock.acquire()
        print('[PROCESS][{}] OK'.format(frame_number))
        try:     
            dict[frame_number] = img_augmented
        finally:
            cv2.imwrite("../tmp/frame_%d.jpg" % frame_number, img_augmented)
            lock.release()

###################################################################################################
# Get Command Line Parser
###################################################################################################
parser = argparse.ArgumentParser()
parser.add_argument('-t', default="", dest='config_profile', help='Config file section to use (tenancy profile)')
parser.add_argument('-p', default="", dest='proxy', help='Set Proxy (i.e. www-proxy-server.com:80) ')
parser.add_argument('-ip', action='store_true', default=False, dest='is_instance_principals', help='Use Instance Principals for Authentication')
parser.add_argument('-dt', action='store_true', default=False, dest='is_delegation_token', help='Use Delegation Token for Authentication')
cmd = parser.parse_args()

###################################################################################################
# Process incoming stream and create thread for each call to OCI AI Vision
###################################################################################################
def stream_process(file_dir, nb_frames_sent,dict,lock) :
    #frame_number = 0
    i=1
    '''
    for frame in iter(lambda: proc.stdout.read(stream_chunk_size), b""):
    time_previous = time.time()
    #logger.debug("  grab stream chunk "+str(i)+" took : " + str(time.time()-time_previous))
    frame_number = frame_number +1
    if i == step:
        in_frame = (np.frombuffer(frame, np.uint8).reshape([height, width, 3]))
        thread = threading.Thread(target=analyzeImage, args=(in_frame,frame_number,dict,lock,))
        thread.start()
        nb_frames_sent= nb_frames_sent + 1        
        logger.debug('step: '+str(i)+' ,number of frames sent to OCI : '+str(nb_frames_sent)+' ,frame number : '+str(frame_number) + ' ,dict size : '+str(len(dict)))
        i = 1
        #cv2.imshow('in_frame', in_frame)
    else :
        i=i+1
    '''
    #cv2.namedWindow("image", cv2.WINDOW_NORMAL)
    vidcap = cv2.VideoCapture(file_dir)
    length = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(length)
    success,image = vidcap.read()
    print('Video Properties: {}x{}'.format(image.shape[1], image.shape[0]))    
    thread_list = []
    while success:
        #if i < 100:
            #cv2.imshow('image', image)
            #key = cv2.waitKey(3000)#pauses for 3 seconds before fetching next image
            #if key == 27:#if ESC is pressed, exit loop
            #    cv2.destroyAllWindows()
            #    break
            thread = threading.Thread(target=analyzeImage, args=(image,i,length,dict,lock,))
            thread.start()
            thread_list.append(thread)
            nb_frames_sent= nb_frames_sent + 1        
            #logger.debug('step: '+str(i)+' ,number of frames sent to OCI : '+str(nb_frames_sent)+' ,frame number : '+str(frame_number) + ' ,dict size : '+str(len(dict)))
            print('[DECOMPOSE][{}/{}]: {}%'.format(i, length, ((i/length) * 100)))

            #c2.imwrite("frame%d.jpg" % count, image)     # save frame as JPEG file      
            success, image = vidcap.read()
            #try:
            # img object is our image
            #    pil_img = Image.fromarray(image)
            #except (AttributeError):
            #    count+= 1
            #    continue
            i += 1
        #else: break
    for x in thread_list:
        x.join() # wait for all threads to finish before moving on.

def cleanup_dir(dir: str):
    for filename in os.listdir(dir):
        file_path = os.path.join(dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
            print('Deleted {}'.format(file_path))        
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))


def create_video(image_folder: str, video_name: str):
    """
    Process for generating images based on a prompt using a specified model.

    Parameters
    ----------
    queue : Queue
        The queue to get the generated images from.
    """
    fps=desired_fps


    image_files = [os.path.join(image_folder,img)
                for img in os.listdir(image_folder)
                if img.endswith(".jpg")]
    file_list_sorted = natsorted(image_files,reverse=False)  # Sort the images
    clip = moviepy.video.io.ImageSequenceClip.ImageSequenceClip(file_list_sorted, fps=fps)
    clip.write_videofile('../output/{}'.format(video_name))
    print('Wrote Video File to ../output/{}'.format(video_name))
    # cleanup directories
    cleanup_dir('../tmp/')
    print('Cleaned tmp dir...')

 
###################################################################################################
# Program start
###################################################################################################
initial_time=datetime.datetime.now()
# Start Header
print_header("VIDEO PROCESSER v1 Started at {}".format(str(initial_time.strftime("%Y-%m-%d %H:%M:%S"))))
logger = logging.getLogger() 
# configuring the logger to info log level 
#logging.basicConfig(level=logging.DEBUG) 
time_initial = time.time()
# create auth from OCI Cli SDK Python 
config, signer = create_signer(cmd.config_profile, cmd.is_instance_principals, cmd.is_delegation_token)
# Initialize AI Vision client with default config file
ai_vision_client = oci.ai_vision.AIServiceVisionClient(config=config, service_endpoint="https://vision.aiservice.eu-frankfurt-1.oci.oraclecloud.com")
# You can change the endpoint with the one with the best latency, example : https://vision.aiservice.eu-frankfurt-1.oci.oraclecloud.com or https://vision.aiservice.eu-madrid-1.oci.oraclecloud.com
# Initialize Notification Service client with default config file
ons_client = oci.ons.NotificationDataPlaneClient(config=config)
# Variables initialization
dict = {}
items_notified = []
nb_frames_sent= 0
nb_frames_processed = 0
width= 960
height = 720
step = int(60/desired_fps)
stream_chunk_size=width * height * 3
lock = threading.Lock()
# Video writer FLV, MPEG-TS or Ogg Theora
out = cv2.VideoWriter(file_to_write, cv2.VideoWriter_fourcc(*'DIVX'), desired_fps, (width,height))
# Execute the command and generate a binary video stream in stdout
proc = sp.Popen(cmd_to_execute, stdout=sp.PIPE, shell=True, cwd=dir_path, bufsize=10**8)

# execution of stream_process needs to be
# threaded and blocking, in order not to
# miss frames
thread = threading.Thread(target=stream_process, args=(file_dir, nb_frames_sent,dict,lock,))
thread.start()
thread.join()
#stream_process(file_dir, nb_frames_sent,dict,lock,)

# write into video file
create_video(image_folder='../tmp/', video_name='output.mp4')
