# -*- coding: utf-8 -*-
import os
import re
import json
from datetime import datetime, timedelta
import requests
import time

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.storage.blob import ResourceTypes, AccountSasPermissions, generate_account_sas


def upload_blob(connection_string, container_name, local_file_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    print("\nUploading to Azure Storage as blob:\n\t" + local_file_name)

    with open(local_file_name, "rb") as data:
        blob_client.upload_blob(data)
    
def download_blob(connection_string, container_name, local_file_name, blob_name):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    print("\nDownloading blob to \n\t" + local_file_name)

    with open(local_file_name, "wb") as download_file:
        download_file.write(blob_client.download_blob().readall())

def get_sas_token(connection_string):
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    sas_token = generate_account_sas(
        blob_service_client.account_name,
        account_key=blob_service_client.credential.account_key,
        resource_types=ResourceTypes(object=True),
        permission=AccountSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    print(sas_token)
    return sas_token

def start_transcription(storage_account, container_name, object_name, transcription_name, locale, subscription_key, sas_token):
    container_url = 'https://' + storage_account + '.blob.core.windows.net/' + container_name

    url = 'https://japaneast.cris.ai/api/speechtotext/v2.0/transcriptions'
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json',
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    payload = {
        "recordingsUrl": container_url + '/' + object_name + '?' + sas_token,
        "locale": locale,
        "name": transcription_name,
        "properties": {
            "TranscriptionResultsContainerUrl" : container_url + service_sas_url
        }
    }

    r = requests.post(url, data=json.dumps(payload), headers=headers)
    print(r)
    pass

def get_transcription_status(transcription_name, subscription_key):
    url = 'https://japaneast.cris.ai/api/speechtotext/v2.0/transcriptions'
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json',
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    r = requests.get(url, headers=headers)
    response = json.loads(r.text)

    for res in response:
        if res['name'] == transcription_name:
            return res['status']

def get_transcription_result_url(transcription_name, subscription_key):
    url = 'https://japaneast.cris.ai/api/speechtotext/v2.0/transcriptions'
    headers = {
        'content-type': 'application/json',
        'accept': 'application/json',
        'Ocp-Apim-Subscription-Key': subscription_key,
    }
    r = requests.get(url, headers=headers)
    response = json.loads(r.text)

    for res in response:
        if res['name'] == transcription_name:
            return res['resultsUrls']['channel_0']

def get_transcript_from_file(file_name):
    json_open = open(file_name, 'r', encoding='utf-8')
    json_load = json.load(json_open)

    transcript = ''
    for audio_file_result in json_load['AudioFileResults']:
        for combined_result in audio_file_result['CombinedResults']:
            transcript += combined_result['Display'] + '\n'
    
    return transcript

if __name__ == "__main__":
    file_name = os.environ['FILE_NAME']
    storage_account = os.environ['AZURE_STORAGE_ACCOUNT']
    connection_string = os.environ['AZURE_STORAGE_CONNECTION_STRING']
    container_name = os.environ['AZURE_STORAGE_CONTAINER_NAME']
    subscription_key = os.environ['AZURE_SUBSCRIPTION_KEY']
    service_sas_url = os.environ['AZURE_SERVICE_SAS_URL']
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)

    encoding_type = file_name[file_name.rfind('.') + 1:].lower()
    if encoding_type not in ['wav']:
        sys.exit()

    file_path = os.path.join(os.path.dirname(__file__), file_name)
    object_name = datetime.now().strftime('%Y%m%d-%H%M%S-') + file_name

    upload_blob(connection_string, container_name, file_path, object_name)

    sas_token = get_sas_token(connection_string)

    transcription_name = re.sub(r'[^a-zA-Z0-9._-]', '', object_name)
    transcription_name = transcription_name.replace('.', '_')

    start_transcription(storage_account, container_name, object_name, transcription_name, subscription_key, sas_token)

    while True:
        status = get_transcription_status(transcription_name, subscription_key)
        print(status)
        if status == 'Succeeded':
            result_url = get_transcription_result_url(transcription_name, subscription_key)
            print(result_url)
            break
        time.sleep(1)
    
    download_file_name = result_url[result_url.rfind('/') + 1:]
    download_blob(connection_string, container_name, download_file_name, download_file_name)
    transcript = get_transcript_from_file(download_file_name)
    print(transcript)
