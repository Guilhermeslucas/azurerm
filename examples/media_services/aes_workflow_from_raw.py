"""
Copyright (c) 2016, Marcelo Leal
Description: Simple Azure Media Services Python library
License: MIT (see LICENSE.txt file for details)
"""
import os
import re
import json
import azurerm
import time
#import pytz
import urllib
import logging
import datetime
from azure.storage.blob import BlockBlobService
from azure.storage.blob import ContentSettings

###########################################################################################
##### DISCLAIMER ##### ##### DISCLAIMER ##### ##### DISCLAIMER ##### ##### DISCLAIMER #####
###########################################################################################

# ALL CODE IN THIS DIRECTOY (INCLUDING THIS FILE) ARE EXAMPLE CODES THAT  WILL  ACT ON YOUR 
# AMS ACCOUNT.  IT ASSUMES THAT THE AMS ACCOUNT IS CLEAN (e.g.: BRAND NEW), WITH NO DATA OR 
# PRODUCTION CODE ON IT.  DO NOT, AGAIN: DO NOT RUN ANY EXAMPLE CODE AGAINST PRODUCTION AMS
# ACCOUNT!  IF YOU RUN ANY EXAMPLE CODE AGAINST YOUR PRODUCTION  AMS ACCOUNT,  YOU CAN LOSE 
# DATA, AND/OR PUT YOUR AMS SERVICES IN A DEGRADED OR UNAVAILABLE STATE. BE WARNED!

###########################################################################################
##### DISCLAIMER ##### ##### DISCLAIMER ##### ##### DISCLAIMER ##### ##### DISCLAIMER #####
###########################################################################################

# Load Azure app defaults
try:
	with open('config.json') as configFile:
		configData = json.load(configFile)
except FileNotFoundError:
	print_phase_message("ERROR: Expecting config.json in current folder")
	sys.exit()

account_name = configData['accountName']
account_key = configData['accountKey']
sto_account_name = configData['sto_accountName']
log_name = configData['logName']
log_level = configData['logLevel']
purge_log = configData['purgeLog']

#Initialization...
print ("\n-----------------------= AMS Py =----------------------");
print ("Simple Python Library for Azure Media Services REST API");
print ("-------------------------------------------------------\n");

#Remove old log file if requested (default behavior)...
if (purge_log.lower() == "yes"):
        if (os.path.isfile(log_name)):
                os.remove(log_name);

#Basic Logging...
logging.basicConfig(format='%(asctime)s - %(levelname)s:%(message)s', level=log_level, filename=log_name)

# Get the access token...
response = azurerm.get_ams_access_token(account_name, account_key)
resjson = response.json()
access_token = resjson["access_token"]

#Some global vars...
NAME = "movie"
COUNTER = 0;
ENCRYPTION = "1" # 0=None, StorageEncrypted=1, CommonEncryptionProtected=2, EnvelopeEncryptionProtected=4
ENCRYPTION_SCHEME = "StorageEncryption" # StorageEncryption or CommonEncryption.
ISM_NAME = "movie.ism"
VIDEO_NAME = "movie.mp4"
VIDEO_PATH = "assets/movie.mp4"
ASSET_FINAL_NAME = "mp4encoded"
PROCESSOR_NAME = "Media Encoder Standard"
AUTH_POLICY = '{"Name":"Open Authorization Policy"}'
KEY_DELIVERY_TYPE = "2" # 1=PlayReady, 2=AES Envelope Encryption
SCALE_UNIT = "1" # This will set the Scale Unit of the Streaming Unit to 1 (Each SU = 200mbs)
JSON_ENCODE_PROFILE_PATH = "presets/h264_multiple_bitrate_720p_profile.json"

# Just a simple wrapper function to print the title of each of our phases to the console...
def print_phase_header(message):
	global COUNTER;
	print("\n[" + str("%02d" % int(COUNTER)) + "] >>> " +  message)
	COUNTER += 1;

# This wrapper function prints our messages to the console with a timestamp...
def print_phase_message(message):
	time_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	print(str(time_stamp) + ": " +  message)

### get ams redirected url
response = azurerm.get_url(access_token)
if (response.status_code == 200):
        ams_redirected_rest_endpoint = str(response.url)
else:
        print_phase_message("GET Status: " + str(response.status_code) + " - Getting Redirected URL ERROR." + str(response.content))
        exit(1);

### PRE-REQ We need to have a Content key to use for AES Encription and
# at least 1 ("one") scale unit at the streaming endpoint (e.g.: default).
# Here you can download a sample to create the Content Key for you:
# https://github.com/msleal/create_ams_aeskey
# The streaming endpoint will be scaled for you (to "1" scale unit).
print_phase_header("Checking the AES Content Key and Setting Streaming Endpoint Scale Unit")
response = azurerm.list_content_key(access_token)
if (response.status_code == 200):
	resjson = response.json()
	count = len(resjson['d']['results']);
	if (count > 0):
		contentkey_id = str(resjson['d']['results'][0]['Id'])
		protectionkey_id = str(resjson['d']['results'][0]['ProtectionKeyId'])
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("AES Content Key Id......................: " + contentkey_id)
		print_phase_message("AES Content Key Name....................: " + str(resjson['d']['results'][0]['Name']))
		print_phase_message("AES Content Protection Key Id...........: " + protectionkey_id)
		print_phase_message("AES Content Key Checksum................: " + str(resjson['d']['results'][0]['Checksum']))
	else:
		print_phase_message("ERROR: AES Content Key Not Found. ")
		print_phase_message("Please create an AES Content Key and execute the script again. ")
		print_phase_message("Sample script to create one: https://github.com/msleal/create_ams_aeskey\n")
		exit(1);
		
else:
	print_phase_message("GET Status.............................: " + str(response.status_code) + " - AES Content Key Listing ERROR." + str(response.content))
	exit(1);

# list and get the id of the default streaming endpoint
print("")
response = azurerm.list_streaming_endpoint(access_token)
if (response.status_code == 200):
	resjson = response.json()
	for ea in resjson['d']['results']:
		print_phase_message("POST Status.............................: " + str(response.status_code))
		print_phase_message("Streaming Endpoint Id...................: " + ea['Id'])
		print_phase_message("Streaming Endpoint Name.................: " + ea['Name'])
		#print_phase_message("Streaming Endpoint Description..........: " + ea['Description'])
		if (ea['Name'] == 'default'):
			streaming_endpoint_id = ea['Id'];
else:
        print_phase_message("POST Status.............................: " + str(response.status_code) + " - Streaming Endpoint Creation ERROR." + str(response.content))

# scale the default streaming endpoint
print("")
response = azurerm.scale_streaming_endpoint(access_token, streaming_endpoint_id, SCALE_UNIT)
if (response.status_code == 202) or (response.status_code == 204):
	print_phase_message("POST Status.............................: " + str(response.status_code))
	print_phase_message("Streaming Endpoint SU Configured to.....: " + SCALE_UNIT)
else:
	print_phase_message("GET Status.............................: " + str(response.status_code) + " - Streaming Endpoint Scaling ERROR." + str(response.content))
	exit(1);

######################### PHASE 1: UPLOAD and VALIDATE #########################
### create an asset
print_phase_header("Creating a Media Asset")
response = azurerm.create_media_asset(access_token, NAME)
if (response.status_code == 201):
	resjson = response.json()
	asset_id = str(resjson['d']['Id']);
	print_phase_message("POST Status.............................: " + str(response.status_code))
	print_phase_message("Media Asset Name........................: " + NAME)
	print_phase_message("Media Asset Id..........................: " + asset_id)
else:
	print_phase_message("POST Status.............................: " + str(response.status_code) + " - Media Asset: '" + NAME + "' Creation ERROR." + str(response.content))

### list an asset
print_phase_header("Listing a Media Asset")
response = azurerm.list_media_asset(access_token, asset_id)
if (response.status_code == 200):
	resjson = response.json()
	asset_uri = str(resjson['d']['Uri'])
	print_phase_message("GET Status..............................: " + str(response.status_code))
	print_phase_message("Media Asset Name........................: " + str(resjson['d']['Name']))
	print_phase_message("Media Asset Encryption..................: " + str(azurerm.translate_asset_options(resjson['d']['Options'])))
	print_phase_message("Media Asset Storage Account Name........: " + str(resjson['d']['StorageAccountName']))
	print_phase_message("Media Asset Uri.........................: " + asset_uri)
else:
	print_phase_message("GET Status..............................: " + str(response.status_code) + " - Media Asset: '" + asset_id + "' Listing ERROR." + str(response.content))

### create an assetfile
print_phase_header("Creating a Media Assetfile (for the video file)")
response = azurerm.create_media_assetfile(access_token, asset_id, VIDEO_NAME, "false", "false")
if (response.status_code == 201):
	resjson = response.json()
	video_assetfile_id = str(resjson['d']['Id']);
	print_phase_message("POST Status.............................: " + str(response.status_code))
	print_phase_message("Media Assetfile Name....................: " + str(resjson['d']['Name']))
	print_phase_message("Media Assetfile Id......................: " + video_assetfile_id)
	print_phase_message("Media Assetfile IsPrimary...............: " + str(resjson['d']['IsPrimary']))
else:
	print_phase_message("POST Status: " + str(response.status_code) + " - Media Assetfile: '" + VIDEO_NAME + "' Creation ERROR." + str(response.content))

### create an asset access policy
print_phase_header("Creating an Asset Access Policy")
duration = "440"
response = azurerm.create_asset_accesspolicy(access_token, "NewUploadPolicy", duration, "2")
if (response.status_code == 201):
	resjson = response.json()
	write_accesspolicy_id = str(resjson['d']['Id']);
	print_phase_message("POST Status.............................: " + str(response.status_code))
	print_phase_message("Asset Access Policy Id..................: " + write_accesspolicy_id)
	print_phase_message("Asset Access Policy Duration/min........: " + str(resjson['d']['DurationInMinutes']))
else:
	print_phase_message("POST Status: " + str(response.status_code) + " - Asset Access Policy Creation ERROR." + str(response.content))

### list an asset access policies
print_phase_header("Listing a Asset Access Policies")
response = azurerm.list_asset_accesspolicy(access_token)
if (response.status_code == 200):
	resjson = response.json()
	print_phase_message("GET Status..............................: " + str(response.status_code))
	for ap in resjson['d']['results']:
		print_phase_message("Asset Access Policie Id.................: " + str(ap['Id']))
else:
	print_phase_message("GET Status: " + str(response.status_code) + " - Asset Access Policy List ERROR." + str(response.content))

### create a sas locator
print_phase_header("Creating a SAS Locator")
## INFO: If you need to upload your files immediately, you should set your StartTime value to five minutes before the current time.
#This is because there may be clock skew between your client machine and Media Services.
#Also, your StartTime value must be in the following DateTime format: YYYY-MM-DDTHH:mm:ssZ (for example, "2014-05-23T17:53:50Z").
# EDITED: Not providing starttime is the best approach to be able to upload a file immediatly...
#starttime = datetime.datetime.now(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%SZ")
#response = azurerm.create_sas_locator(access_token, asset_id, write_accesspolicy_id, starttime)
response = azurerm.create_sas_locator(access_token, asset_id, write_accesspolicy_id)
if (response.status_code == 201):
	resjson = response.json()
	saslocator_id = str(resjson['d']['Id']);
	saslocator_baseuri = str(resjson['d']['BaseUri']);
	sto_asset_name = os.path.basename(os.path.normpath(saslocator_baseuri))
	saslocator_cac = str(resjson['d']['ContentAccessComponent']);
	print_phase_message("POST Status.............................: " + str(response.status_code))
	print_phase_message("SAS URL Locator StartTime...............: " + str(resjson['d']['StartTime']))
	print_phase_message("SAS URL Locator Id......................: " + saslocator_id)
	print_phase_message("SAS URL Locator Base URI................: " + saslocator_baseuri)
	print_phase_message("SAS URL Locator Content Access Component: " + saslocator_cac)
else:
	print_phase_message("POST Status: " + str(response.status_code) + " - SAS URL Locator Creation ERROR." + str(response.content))

### list the sas locator
print_phase_header("Listing a SAS Locator")
response = azurerm.list_sas_locator(access_token)
if (response.status_code == 200):
	resjson = response.json()
	print_phase_message("GET Status..............................: " + str(response.status_code))
	for sl in resjson['d']['results']:
		print_phase_message("SAS Locator Id..........................: " + str(sl['Id']))
else:
	print_phase_message("GET Status..............................: " + str(response.status_code) + " - SAS Locator List ERROR." + str(response.content))

### Uploads
block_blob_service = BlockBlobService(account_name=sto_account_name, sas_token=saslocator_cac[1:])

### upload the video file
print_phase_header("Uploading the Video File")
with open(VIDEO_PATH, mode='rb') as file:
        video_content = file.read()
        video_content_length = len(video_content)

response = block_blob_service.create_blob_from_path(
		sto_asset_name,
		VIDEO_NAME,
		VIDEO_PATH,
		max_connections=5,
		content_settings=ContentSettings(content_type='video/mp4')
	)
if (response == None):
        print_phase_message("PUT Status..............................: 201")
        print_phase_message("Video File Uploaded.....................: OK")

### update the assetfile
print_phase_header("Updating the Video Assetfile")
response = azurerm.update_media_assetfile(access_token, asset_id, video_assetfile_id, video_content_length, VIDEO_NAME)
if (response.status_code == 204):
	print_phase_message("MERGE Status............................: " + str(response.status_code))
	print_phase_message("Assetfile Content Length Updated........: " + str(video_content_length))
else:
	print_phase_message("MERGE Status............................: " + str(response.status_code) + " - Assetfile: '" + VIDEO_NAME + "' Update ERROR." + str(response.content))

### delete the locator
print_phase_header("Deleting the Locator")
response = azurerm.delete_sas_locator(access_token, saslocator_id)
if (response.status_code == 204):
	print_phase_message("DELETE Status...........................: " + str(response.status_code))
	print_phase_message("SAS URL Locator Deleted.................: " + saslocator_id)
else:
	print_phase_message("DELETE Status...........................: " + str(response.status_code) + " - SAS URL Locator: '" + saslocator_id + "' Delete ERROR." + str(response.content))

### delete the asset access policy
print_phase_header("Deleting the Acess Policy")
response = azurerm.delete_asset_accesspolicy(access_token, write_accesspolicy_id)
if (response.status_code == 204):
	print_phase_message("DELETE Status...........................: " + str(response.status_code))
	print_phase_message("Asset Access Policy Deleted.............: " + write_accesspolicy_id)
else:
	print_phase_message("DELETE Status...........................: " + str(response.status_code) + " - Asset Access Policy: '" + write_accesspolicy_id + "' Delete ERROR." + str(response.content))

### get the media processor
print_phase_header("Getting the Media Processor")
response = azurerm.list_media_processor(access_token)
if (response.status_code == 200):
        resjson = response.json()
        print_phase_message("GET Status..............................: " + str(response.status_code))
        for mp in resjson['d']['results']:
                if(str(mp['Name']) == PROCESSOR_NAME):
                        processor_id = str(mp['Id'])
                        print_phase_message("MEDIA Processor Id......................: " + processor_id)
                        print_phase_message("MEDIA Processor Name....................: " + PROCESSOR_NAME)
else:
        print_phase_message("GET Status: " + str(response.status_code) + " - Media Processors Listing ERROR." + str(response.content))

## create a media encoding job
print_phase_header("Creating a Media Job to encode the mezzanine")
with open(JSON_ENCODE_PROFILE_PATH, mode='r') as file:
        profile_content = file.read()

response = azurerm.encode_mezzanine_asset(access_token, processor_id, asset_id, ASSET_FINAL_NAME, profile_content)
if (response.status_code == 201):
	resjson = response.json()
	job_id = str(resjson['d']['Id']);
	print_phase_message("POST Status.............................: " + str(response.status_code))
	print_phase_message("Media Job Id............................: " + job_id)
else:
	print_phase_message("POST Status.............................: " + str(response.status_code) + " - Media Job Creation ERROR." + str(response.content))

### list a media job
print_phase_header("Getting the Media Job Status")
flag = 1
while (flag):
	response = azurerm.list_media_job(access_token, job_id)
	if (response.status_code == 200):
		resjson = response.json()
		job_state = str(resjson['d']['State'])
		if (resjson['d']['EndTime'] != None):
			joboutputassets_uri = resjson['d']['OutputMediaAssets']['__deferred']['uri']
			flag = 0;
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("Media Job Status........................: " + azurerm.translate_job_state(job_state))
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - Media Job: '" + asset_id + "' Listing ERROR." + str(response.content))
	time.sleep(5);

######################### PHASE 2: PROTECT and STREAM #########################
### delete an asset
if (azurerm.translate_job_state(job_state) == 'Finished'):
	### delete an asset
	print_phase_header("Deleting the Original Asset")
	response = azurerm.delete_media_asset(access_token, asset_id)
	if (response.status_code == 204):
		print_phase_message("DELETE Status...........................: " + str(response.status_code))
		print_phase_message("Asset Deleted...........................: " + asset_id)
	else:
		print_phase_message("DELETE Status...........................: " + str(response.status_code) + " - Asset: '" + asset_id + "' Delete ERROR." + str(response.content))

	## getting the encoded asset id
	print_phase_header("Getting the Encoded Media Asset Id")
	response = azurerm.get_url(access_token, joboutputassets_uri, False)
	if (response.status_code == 200):
		resjson = response.json()
		encoded_asset_id = resjson['d']['results'][0]['Id']
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("Encoded Media Asset Id..................: " + encoded_asset_id)
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - Media Job Output Asset: '" + job_id + "' Getting ERROR." + str(response.content))

	### link a content key
	print_phase_header("Linking the Content Key to the Encoded Asset")
	response = azurerm.link_asset_content_key(access_token, encoded_asset_id, contentkey_id, ams_redirected_rest_endpoint)
	if (response.status_code == 204):
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("Media Content Key Linked................: OK")
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - Media Asset: '" + encoded_asset_id + "' Content Key Linking ERROR." + str(response.content))

	### configure content key authorization policy
	print_phase_header("Creating the Content Key Authorization Policy")
	response = azurerm.create_contentkey_authorization_policy(access_token, AUTH_POLICY)
	if (response.status_code == 201):
		resjson = response.json()
		authorization_policy_id = str(resjson['d']['Id']);
		print_phase_message("POST Status.............................: " + str(response.status_code))
		print_phase_message("CK Authorization Policy Id..............: " + authorization_policy_id)
	else:
		print_phase_message("POST Status.............................: " + str(response.status_code) + " - Content Key Authorization Policy Creation ERROR." + str(response.content))

	### configure asset delivery policy
	print_phase_header("Creating the Content Key Authorization Policy Options")
	response = azurerm.create_contentkey_authorization_policy_options(access_token)
	if (response.status_code == 201):
		resjson = response.json()
		authorization_policy_options_id = str(resjson['d']['Id']);
		print_phase_message("POST Status.............................: " + str(response.status_code))
		print_phase_message("CK Authorization Policy Options Id......: " + authorization_policy_options_id)
	else:
		print_phase_message("POST Status.............................: " + str(response.status_code) + " - Content Key Authorization Policy Options Creation ERROR." + str(response.content))

	### link a contentkey authorization policies with options
	print ("Linking the Content Key Authorization Policy with Options")
	response = azurerm.link_contentkey_authorization_policy(access_token, authorization_policy_id, authorization_policy_options_id, ams_redirected_rest_endpoint)
	if (response.status_code == 204):
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("CK Authorization Policy Linked..........: OK")
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - Content Key Authorization Policy '" + authorization_policy_id + "' Linking ERROR." + str(response.content))

	### link a contentkey authorization policies with options
	print_phase_header("Add the Authorization Policy to the Content Key")
	response = azurerm.add_authorization_policy(access_token, contentkey_id, authorization_policy_id)
	if (response.status_code == 204):
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("Authorization Policy Added..............: OK")
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - Authorization Policy: '" + authorization_policy_id + "' Adding ERROR." + str(response.content))

	### get the delivery url
	print_phase_header("Getting the Key Delivery URL")
	response = azurerm.get_key_delivery_url(access_token, contentkey_id, KEY_DELIVERY_TYPE)
	if (response.status_code == 200):
		resjson = response.json()
		keydelivery_url = re.sub("\?.*$","", str(resjson['d']['GetKeyDeliveryUrl']));
		print_phase_message("POST Status.............................: " + str(response.status_code))
		print_phase_message("Key Delivery URL........................: " + keydelivery_url)
	else:
		print_phase_message("POST Status.............................: " + str(response.status_code) + " - Key Delivery: '" + contentkey_id + "' URL Getting ERROR." + str(response.content))

	### create asset delivery policy
	print_phase_header("Creating Asset Delivery Policy")
	response = azurerm.create_asset_delivery_policy(access_token, account_name, keydelivery_url)
	if (response.status_code == 201):
		resjson = response.json()
		assetdeliverypolicy_id = str(resjson['d']['Id']);
		print_phase_message("POST Status.............................: " + str(response.status_code))
		print_phase_message("Asset Delivery Policy Id................: " + assetdeliverypolicy_id)
	else:
		print_phase_message("POST Status.............................: " + str(response.status_code) + " - Asset Delivery Policy Creating ERROR." + str(response.content))

	### link the asset with the asset delivery policy
	print_phase_header("Linking the Asset with the Asset Delivery Policy")
	response = azurerm.link_asset_delivery_policy(access_token, encoded_asset_id, assetdeliverypolicy_id, ams_redirected_rest_endpoint)
	if (response.status_code == 204):
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("Asset Delivery Policy Linked............: OK")
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - Asset: '" + encoded_asset_id + "' Delivery Policy Linking ERROR." + str(response.content))

	### create an asset access policy
	print_phase_header("Creating an Asset Access Policy")
	duration = "43200"
	response = azurerm.create_asset_accesspolicy(access_token, "NewViewAccessPolicy", duration)
	if (response.status_code == 201):
		resjson = response.json()
		view_accesspolicy_id = str(resjson['d']['Id']);
		print_phase_message("POST Status.............................: " + str(response.status_code))
		print_phase_message("Asset Access Policy Id..................: " + view_accesspolicy_id)
		print_phase_message("Asset Access Policy Duration/min........: " + str(resjson['d']['DurationInMinutes']))
	else:
		print_phase_message("POST Status: " + str(response.status_code) + " - Asset Access Policy Creation ERROR." + str(response.content))

	### create an ondemand streaming locator
	print_phase_header("Create an OnDemand Streaming Locator")
	#starttime = datetime.datetime.now(pytz.timezone(time_zone)).strftime("%Y-%m-%dT%H:%M:%SZ")
	#response = azurerm.create_ondemand_streaming_locator(access_token, encoded_asset_id, view_accesspolicy_id, starttime)
	response = azurerm.create_ondemand_streaming_locator(access_token, encoded_asset_id, view_accesspolicy_id)
	if (response.status_code == 201):
		resjson = response.json()
		ondemandlocator_id = str(resjson['d']['Id']);
		print_phase_message("GET Status..............................: " + str(response.status_code))
		print_phase_message("OnDemand Streaming Locator Id...........: " + ondemandlocator_id)
		print_phase_message("OnDemand Streaming Locator Path.........: " + str(resjson['d']['Path']))
		print_phase_message("HLS + AES URL...........................: " + str(resjson['d']['Path']) + ISM_NAME + "/manifest(format=m3u8-aapl)")
		print ("\n -> We got here? Cool! Now you just need the popcorn...")
	else:
		print_phase_message("GET Status..............................: " + str(response.status_code) + " - OnDemand Streaming Locator Creating ERROR." + str(response.content))
else:
	print ("\n Something went wrong... we could not encode the Mezzanine Asset!")
