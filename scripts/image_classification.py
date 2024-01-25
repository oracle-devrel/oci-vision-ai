# This is an automatically generated code sample.
# To make this code sample work in your Oracle Cloud tenancy,
# please replace the values for any parameters whose current values do not fit
# your use case (such as resource IDs, strings containing ‘EXAMPLE’ or ‘unique_id’, and
# boolean, number, and enum parameters with values not fitting your use case).

import oci
import logging
import sys
import ujson as json
# Create a default config using DEFAULT profile in default location
# Refer to
# https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm#SDK_and_CLI_Configuration_File
# for more info
config = oci.config.from_file()

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
                feature_type="IMAGE_CLASSIFICATION",
                max_results=130,
                #model_id="ocid1.test.oc1..<unique_ID>EXAMPLE-modelId-Value"
                )],
        image=oci.ai_vision.models.ObjectStorageImageDetails(
            source="OBJECT_STORAGE", # OR 'INLINE'
            namespace_name="axywji1aljc2",
            bucket_name="vision-bucket",
            object_name="2.jpeg"),
        compartment_id="ocid1.compartment.oc1..aaaaaaaauyfykbiauv4nntvl3b57ydx3wcrqsnax7bbbvhov4vmdvqo2nqca"),
    opc_request_id="vision-ai-test-nacho-{}".format(random_number))

# Get the data from response
#print(analyze_image_response.data)

# Process and analyze the JSON response to our convenience

#print(str(analyze_image_response.data))
jdata = json.loads(str(analyze_image_response.data))

# First, we will check the consistency of the JSON object.
try:
    jdata['labels']
    jdata['ontology_classes']
except KeyError as e:
    print('Error in JSON data structure. Exiting...')
    sys.exit(-100)

# Now, we will load the 5 best responses from the model, with the
# highest confidence as the best response

# list of responses
labels = jdata['labels']
for x in range(0, 3):
    print('Most Probable Object {} Confidence {}%'.format(
        labels[x]['name'],
        labels[x]['confidence']*100
    ))

print('x'*10)
most_probable_list = labels[0:3]

highly_probable_list = list()
# Instead of taking only the most probable in the picture,
# take all attributes with a confidence higher than 90%.
for x in range(len(labels)):
    if labels[x]['confidence']*100 > 90.0:
        highly_probable_list.append(labels[x])

# Then, we use the list:
for x in range(len(highly_probable_list)):
    print('Highly Probable Object {} Confidence {}%'.format(
        labels[x]['name'],
        labels[x]['confidence']*100
    ))

# If there's something relating labels[x]['name'] to ontology_classes,
# or something appears with that name,
# we can use those nouns as well to describe what's in the picture.

