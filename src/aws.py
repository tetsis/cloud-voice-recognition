# -*- coding: utf-8 -*-
import boto3
from datetime import datetime
import time
import json

def upload_object(bucket_name, source_file_name, destination_objcet_name):
    s3 = boto3.resource('s3')
    bucket = s3.Bucket(bucket_name)
    bucket.upload_file(source_file_name, destination_objcet_name)

def download_file(bucket_name, object_name, file_name):
    s3 = boto3.client('s3')
    s3.download_file(bucket_name, object_name, file_name)

def start_job(transcription_job_name, language_code, media_file_uri, output_bucket_name):
    client = boto3.client('transcribe')
    response = client.start_transcription_job(
        TranscriptionJobName=transcription_job_name,
        LanguageCode=language_code,
        Media={
        'MediaFileUri': media_file_uri
        },
        OutputBucketName=output_bucket_name
    )

    return response

def get_transcription_job(transcription_job_name):
    client = boto3.client('transcribe')
    response = client.get_transcription_job(
        TranscriptionJobName=transcription_job_name
    )

    return response


if __name__ == "__main__":
    bucket_name = 'transcribe.nstech'
    file_name = 'news.mp3'
    object_name = datetime.now().strftime('%Y%m%d-%H%M%S-') + file_name
    upload_object(bucket_name, file_name, object_name)
    job_name = object_name.replace('.', '_')

    start_job(job_name, 'ja-JP', 's3://' + bucket_name + '/' + object_name, bucket_name)

    while True:
        response = get_transcription_job(job_name)
        status = response['TranscriptionJob']['TranscriptionJobStatus']
        if status == 'COMPLETED':
            break
        time.sleep(5)

    job_file_name = job_name + '.json'
    download_file(bucket_name, job_file_name, job_file_name)

    job_file_name = '20200307-051324-news_mp3.json'
    f = open(job_file_name, 'r', encoding="utf-8")
    json_dict = json.load(f)
    print(json_dict['results']['transcripts'][0]['transcript'])
