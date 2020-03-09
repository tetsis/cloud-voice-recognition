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
import gcp

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
        language_code = 'ja-JP'
        try:
            language_code = self.get_body_argument('language')
        except MissingArgumentError:
            pass
        job_name = re.sub(r'[^a-zA-Z0-9._-]', '', object_name)
        job_name = job_name.replace('.', '_')

        # Transcribeの処理開始
        response = aws.start_job(job_name, language_code, 's3://' + s3_bucket_name + '/' + object_name, s3_bucket_name)
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

class GcpUploadHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def post(self):
        file = self.request.files['audio'][0]

        file_name = file.filename
        file_name = datetime.now().strftime('%Y%m%d-%H%M%S-') + file_name
        file_path = os.path.join('/tmp', file_name)
        output_file = open(file_path, 'wb')
        output_file.write(file.body)

        # ファイル形式取得
        encoding_type = file_name[file_name.rfind('.') + 1:].lower()
        if encoding_type not in ['wav', 'flac']:
            json_response = json.dumps({'message': 'Unsupported file format'}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        info = None
        sample_rate_hertz = None
        audio_channel_count = None
        if encoding_type == 'wav':
            info = gcp.get_wav_info(file_path)
            sample_rate_hertz = info['framerate']
            audio_channel_count = info['channels']
        elif encoding_type == 'flac':
            info = gcp.get_flac_info(file_path)
            sample_rate_hertz = info['sample_rate']
            audio_channel_count = info['channels']

        # GCSにアップロード
        gcp.upload_blob(gcs_bucket_name, file_path, file_name)

        json_response = json.dumps(
            {
                'object_name': file_name,
                'sample_rate_hertz': sample_rate_hertz,
                'audio_channel_count': audio_channel_count,
            },
            ensure_ascii=False)
        self.write(json_response)

class GcpRecognizeHandler(tornado.web.RequestHandler):
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

        language_code = 'ja-JP'
        try:
            language_code = self.get_body_argument('language')
        except MissingArgumentError:
            pass

        sample_rate_hertz = ''
        try:
            sample_rate_hertz = self.get_body_argument('sample_rate_hertz')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'sample_rate_hertz\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        audio_channel_count = ''
        try:
            audio_channel_count = self.get_body_argument('audio_channel_count')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'audio_channel_count\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        # ファイル形式取得
        encoding_type = object_name[object_name.rfind('.') + 1:].lower()
        if encoding_type not in ['wav', 'flac']:
            json_response = json.dumps({'message': 'Unsupported file format'}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        # Cloud Speech-to-Text実行
        storage_uri = 'gs://' + gcs_bucket_name + '/' + object_name
        operation_name = gcp.sample_long_running_recognize(storage_uri, sample_rate_hertz, audio_channel_count, language_code, encoding_type)

        json_response = json.dumps({'operation_name': operation_name}, ensure_ascii=False)
        self.write(json_response)

class GcpTextHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def get(self):
        operation_name = ''
        try:
            operation_name = self.get_query_argument('operation_name')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'operation_name\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return
        
        done = gcp.check_operation(operation_name, gcp_api_key)
        transcript = ''
        if done:
            transcript = gcp.get_transcript(operation_name, gcp_api_key)
        
        json_response = json.dumps({'done': done, 'transcript': transcript}, ensure_ascii=False)
        self.write(json_response)

if __name__ == "__main__":
    gcs_bucket_name = os.environ.get('GCS_BUCKET_NAME', 'gcs_bucket_name')
    s3_bucket_name = os.environ.get('S3_BUCKET_NAME', 's3_bucket_name')
    gcp_api_key = os.environ.get('GCP_API_KEY', 'gcp_api_key')
    credential_path = os.path.join(os.path.dirname(__file__), '../credentials/GOOGLE_APPLICATION_CREDENTIALS.json')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

    application = tornado.web.Application(
        [
            url(r"/api/text", TextHandler, name='text'),
            url(r"/api/aws/upload", AwsUploadHandler, name='aws_upload'),
            url(r"/api/aws/recognize", AwsRecognizeHandler, name='aws_recognize'),
            url(r"/api/aws/text", AwsTextHandler, name='aws_text'),
            url(r"/api/gcp/upload", GcpUploadHandler, name='gcp_upload'),
            url(r"/api/gcp/recognize", GcpRecognizeHandler, name='gcp_recognize'),
            url(r"/api/gcp/text", GcpTextHandler, name='gcp_text'),
        ],
    )
    server = tornado.httpserver.HTTPServer(application)
    server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()