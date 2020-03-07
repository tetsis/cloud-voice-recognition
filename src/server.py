#!/usr/bin/python3.8
# -*- coding: utf-8 -*-
import os
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.web import url, MissingArgumentError
import json
from datetime import datetime
import re

import aws

class TextHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def get(self):
        id = ''
        try:
            id = self.get_query_argument('id')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'id\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        json_response = json.dumps({'message': 'test'}, ensure_ascii=False)
        self.write(json_response)

class UploadHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def post(self):
        file = self.request.files['audio'][0]

        file_name = datetime.now().strftime('%Y%m%d-%H%M%S-') + file.filename
        file_path = os.path.join('/tmp', file_name)
        blob_name = file_name
        output_file = open(file_path, 'wb')
        output_file.write(file.body)

        # GCSにアップロード
        upload_blob(bucket_name, file_path, blob_name)

        # Speech APIにかける
        operation = sample_long_running_recognize('gs://' + bucket_name + '/' + blob_name)

        json_response = json.dumps({'blob_name': blob_name, 'operation': operation}, ensure_ascii=False)
        self.write(json_response)

class AwsUploadHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def post(self):
        file = self.request.files['audio'][0]

        file_name = file.filename
        file_name = datetime.now().strftime('%Y%m%d-%H%M%S-') + file_name
        file_path = os.path.join('/tmp', file_name)
        output_file = open(file_path, 'wb')
        output_file.write(file.body)

        # S3にアップロード
        aws.upload_object(s3_bucket_name, file_path, file_name)

        json_response = json.dumps({'object_name': file_name}, ensure_ascii=False)
        self.write(json_response)

class AwsRecognizeHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def post(self):
        object_name = ''
        try:
            object_name = self.get_body_argument('object_name')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'object_name\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return
        job_name = re.sub(r'[^a-zA-Z0-9._-]', '', object_name)
        job_name = job_name.replace('.', '_')

        # Transcribeの処理開始
        response = aws.start_job(job_name, 'ja-JP', 's3://' + s3_bucket_name + '/' + object_name, s3_bucket_name)
        status = response['TranscriptionJob']['TranscriptionJobStatus']

        json_response = json.dumps({'status': status, 'job_name': job_name}, ensure_ascii=False)
        self.write(json_response)

class AwsTextHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def get(self):
        job_name = ''
        try:
            job_name = self.get_query_argument('job_name')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'job_name\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        response = aws.get_transcription_job(job_name)
        status = response['TranscriptionJob']['TranscriptionJobStatus']
        transcript = ''
        if status == 'COMPLETED':
            job_file_name = job_name + '.json'
            file_path = os.path.join('/tmp', job_file_name)
            aws.download_file(s3_bucket_name, job_file_name, file_path)

            f = open(file_path, 'r', encoding="utf-8")
            json_dict = json.load(f)
            transcript = json_dict['results']['transcripts'][0]['transcript']

        json_response = json.dumps({'status': status, 'transcript': transcript}, ensure_ascii=False)
        self.write(json_response)

def upload_blob(bucket_name, source_file_name, destination_blob_name):
    # """Uploads a file to the bucket."""
    # bucket_name = "your-bucket-name"
    # source_file_name = "local/path/to/file"
    # destination_blob_name = "storage-object-name"

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    blob.upload_from_filename(source_file_name)


def sample_long_running_recognize(storage_uri):
    # """
    # Transcribe long audio file from Cloud Storage using asynchronous speech
    # recognition

    # Args:
    #     storage_uri URI for audio file in Cloud Storage, e.g. gs://[BUCKET]/[FILE]
    # """

    client = speech_v1.SpeechClient()

    # storage_uri = 'gs://cloud-samples-data/speech/brooklyn_bridge.raw'

    # Sample rate in Hertz of the audio data sent
    sample_rate_hertz = 16000

    # The language of the supplied audio
    language_code = "ja-JP"

    # Encoding of audio data sent. This sample sets this explicitly.
    # This field is optional for FLAC and WAV audio formats.
    encoding = enums.RecognitionConfig.AudioEncoding.FLAC

    config = {
        "sample_rate_hertz": sample_rate_hertz,
        "language_code": language_code,
        "encoding": encoding,
    }
    audio = {"uri": storage_uri}

    operation = client.long_running_recognize(config, audio)

    return operation

if __name__ == "__main__":
    bucket_name = os.environ.get('BUCKET_NAME', 'bucket_name')
    s3_bucket_name = os.environ.get('S3_BUCKET_NAME', 's3_bucket_name')
    api_key = os.environ.get('API_KEY', 'api_key')

    application = tornado.web.Application(
        [
            url(r"/api/text", TextHandler, name='text'),
            url(r"/api/aws/upload", AwsUploadHandler, name='aws_upload'),
            url(r"/api/aws/recognize", AwsRecognizeHandler, name='aws_recognize'),
            url(r"/api/aws/text", AwsTextHandler, name='aws_text'),
        ],
    )
    server = tornado.httpserver.HTTPServer(application)
    server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()