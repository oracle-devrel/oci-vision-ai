# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci
import logging
import sys
import ujson as json
import cv2
from PIL import ImageGrab, Image


# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()


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
        color = (255, 255, 255)
        thickness = 2
        police_size = 1.25
        police_thickness = 3
        cv2.rectangle(img, start_point, end_point, color, thickness)
        cv2.putText(img, image_object["name"], (int(vertex_x + 15), int(vertex_y + box_height + 30)), cv2.FONT_HERSHEY_SIMPLEX, police_size, color, police_thickness, 2)
    
    return img


# Enabling debug logging
logging.getLogger('oci').setLevel(logging.DEBUG)

# Initialize service client with default config file
ai_vision_client = oci.ai_vision.AIServiceVisionClient(config)

import random
random_number = random.randint(0, 500000)
# Send the request to service, some parameters are not required, see API
# doc for more info
analyze_image_response = ai_vision_client.analyze_image(
    analyze_image_details=oci.ai_vision.models.AnalyzeImageDetails(
        features=[
            oci.ai_vision.models.ImageClassificationFeature(
                feature_type="OBJECT_DETECTION",
                max_results=130,
                #model_id="ocid1.test.oc1..<unique_ID>EXAMPLE-modelId-Value"
                )],
        image=oci.ai_vision.models.ObjectStorageImageDetails(
            source="OBJECT_STORAGE", # OR 'INLINE'
            namespace_name="axywji1aljc2",
            bucket_name="vision-bucket",
            object_name="22WHITEGOD1-superJumbo-v2.jpg"),
        compartment_id="ocid1.compartment.oc1..aaaaaaaauyfykbiauv4nntvl3b57ydx3wcrqsnax7bbbvhov4vmdvqo2nqca"),
    opc_request_id="vision-ai-test-nacho-{}".format(random_number))

# Get the data from response
#print(analyze_image_response.data)

# Process and analyze the JSON response to our convenience

print(str(analyze_image_response.data))
jdata = json.loads(str(analyze_image_response.data))

# First, we will check the consistency of the JSON object.
try:
    jdata['image_objects']
    jdata['ontology_classes']
except KeyError as e:
    print('Error in JSON data structure. Exiting...')
    sys.exit(-100)

# Now, we will load the 5 best responses from the model, with the
# highest confidence as the best response

# list of responses
objects = jdata['image_objects'] # list() type
for x in range(len(objects)):
    if objects[x]['confidence'] > 0.8:
        vertices_list = list()
        vertices = objects[x]['bounding_polygon']['normalized_vertices']
        # For each vertex, store it in a list.
        for i in range(0, 4):
            vertices_list.append((vertices[i]['x'], vertices[i]['y']))
        # only process results above X threshold % confidence.
        print('{} [{}%]: {}'.format(
            objects[x]['name'],
            objects[x]['confidence'],
            vertices
        ))

        '''
        img = cv2.imread('../img/22WHITEGOD1-superJumbo-v2.jpg')
        draw_result = draw_object_info(objects, img)
        cv2.imshow('Image', draw_result)

        im_rgb = cv2.cvtColor(draw_result, cv2.COLOR_BGR2RGB)
        pilImage = Image.fromarray(im_rgb)
        pilImage.save('../img/output_object_detection_verify.png', 'PNG')
        cv2.waitKey(5) # show the image for 5 seconds and exit.
        '''


print('x'*10)