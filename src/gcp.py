# -*- coding: utf-8 -*-
from datetime import datetime
import time
import json
import os
import sys
import wave
from mutagen.flac import FLAC

from google.cloud import storage
from google.cloud import speech_v1
from google.cloud.speech_v1 import enums
from google.api_core.exceptions import InvalidArgument

def get_wav_info(file_name):
    wv = wave.open(file_name, 'rb')

    channels = wv.getnchannels()
    print(channels)

    framerate = wv.getframerate()
    print(framerate)

    return {
        'channels': channels,
        'framerate': framerate
    }

def get_flac_info(file_name):
    sound = FLAC(file_name).info
    channels = sound.channels
    sample_rate = sound.sample_rate

    return {
        'channels': channels,
        'sample_rate': sample_rate
    }

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    # """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)

    print(
        "File {} uploaded to {}.".format(
            source_file_name, destination_blob_name
        )
    )

def sample_long_running_recognize(storage_uri, sample_rate_hertz, audio_channel_count, language_code, encoding_type):
    # """
    # Transcribe long audio file from Cloud Storage using asynchronous speech
    # recognition

    # Args:
    #   storage_uri URI for audio file in Cloud Storage, e.g. gs://[BUCKET]/[FILE]
    # """

    client = speech_v1.SpeechClient()

    # storage_uri = 'gs://cloud-samples-data/speech/brooklyn_bridge.raw'

    # Sample rate in Hertz of the audio data sent
    #sample_rate_hertz = 44100

    # The number of channels in the input audio file (optional)
    #audio_channel_count = 2

    # Encoding of audio data sent. This sample sets this explicitly.
    # This field is optional for FLAC and WAV audio formats.
    # FLAC: FLAC, WAV: LINEAR16
    encoding_type = encoding_type.lower()
    if encoding_type not in ['wav', 'flac']:
        return 'Unsupported file format.'
    encoding = enums.RecognitionConfig.AudioEncoding.LINEAR16
    if encoding_type == 'flac':
        encoding = enums.RecognitionConfig.AudioEncoding.FLAC
    config = {
        #"sample_rate_hertz": sample_rate_hertz,
        "language_code": language_code,
        "encoding": encoding,
    }
    audio = {"uri": storage_uri}

    try:
        operation = client.long_running_recognize(config, audio)
    except InvalidArgument as e:
        return e

    print(u"Waiting for operation to complete...")
    response = operation.result()

    transcript = ''
    for result in response.results:
        for alternative in result.alternatives:
            transcript += alternative.transcript + '\n'
    
    return transcript

if __name__ == "__main__":
    gcs_bucket_name = 'nstech-cloudsandbox'
    file_name = 'aramaki.flac'
    encoding_type = file_name[file_name.rfind('.') + 1:].lower()
    if encoding_type not in ['wav', 'flac']:
        sys.exit()

    file_path = os.path.join(os.path.dirname(__file__), file_name)
    credential_path = os.path.join(os.path.dirname(__file__), '../api/GOOGLE_APPLICATION_CREDENTIALS.json')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path
    object_name = datetime.now().strftime('%Y%m%d-%H%M%S-') + file_name

    info = None
    if encoding_type == 'wav':
        info = get_wav_info(file_path)
    elif encoding_type == 'flac':
        info = get_flac_info(file_path)
    print(info)

    #upload_blob(gcs_bucket_name, file_path, object_name)

    #storage_uri = 'gs://' + gcs_bucket_name + '/' + object_name
    #sample_rate_hertz = info['framerate']
    #audio_channel_count = info['channels']
    #language_code = "ja-JP"

    #transcript = sample_long_running_recognize(storage_uri, sample_rate_hertz, audio_channel_count, language_code, encoding_type)
    #print('result: {}'.format(transcript))