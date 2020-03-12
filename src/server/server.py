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
import azure_speech
import lib

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
        if encoding_type not in ['wav', 'flac', 'mp3']:
            json_response = json.dumps({'message': 'Unsupported file format'}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return
        
        # mp3の場合はwavに変換
        if encoding_type == 'mp3':
            new_file_path = lib.convert_to_wav_from_mp3(file_path)
            if new_file_path:
                file_path = new_file_path
                file_name = file_path[file_path.rfind('/') + 1:]
                encoding_type = 'wav'
            else:
                json_response = json.dumps({'message': 'Cannot convert mp3 file'}, ensure_ascii=False)
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

class AzureUploadHandler(tornado.web.RequestHandler):
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
        if encoding_type not in ['wav', 'mp3']:
            json_response = json.dumps({'message': 'Unsupported file format'}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        # mp3の場合はwavに変換
        if encoding_type == 'mp3':
            new_file_path = lib.convert_to_wav_from_mp3(file_path)
            if new_file_path:
                file_path = new_file_path
                file_name = file_path[file_path.rfind('/') + 1:]
                encoding_type = 'wav'
            else:
                json_response = json.dumps({'message': 'Cannot convert mp3 file'}, ensure_ascii=False)
                self.set_status(400)
                self.write(json_response)
                return


        # コンテナにアップロード
        azure_speech.upload_blob(azure_connection_string, azure_container_name, file_path, file_name)

        json_response = json.dumps(
            {
                'object_name': file_name,
            },
            ensure_ascii=False)
        self.write(json_response)

class AzureRecognizeHandler(tornado.web.RequestHandler):
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

        locale = 'ja-JP'
        try:
            locale = self.get_body_argument('language')
        except MissingArgumentError:
            pass

        # ファイル形式取得
        encoding_type = object_name[object_name.rfind('.') + 1:].lower()
        if encoding_type not in ['wav']:
            json_response = json.dumps({'message': 'Unsupported file format'}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return

        # Speeche Service実行
        transcription_name = re.sub(r'[^a-zA-Z0-9._-]', '', object_name)
        transcription_name = transcription_name.replace('.', '_')

        sas_token = azure_speech.get_sas_token(azure_connection_string)
        azure_speech.start_transcription(azure_storage_account, azure_container_name, object_name, transcription_name, locale, azure_subscription_key, sas_token, azure_service_sas_url)

        json_response = json.dumps({'transcription_name': transcription_name}, ensure_ascii=False)
        self.write(json_response)

class AzureTextHandler(tornado.web.RequestHandler):
    def set_default_headers(self):
        self.set_header('Access-Control-Allow-Origin', '*')

    def get(self):
        transcription_name = ''
        try:
            transcription_name = self.get_query_argument('transcription_name')
        except MissingArgumentError:
            json_response = json.dumps({'message': 'Not enough argument \'transcription_name\''}, ensure_ascii=False)
            self.set_status(400)
            self.write(json_response)
            return
        
        status = azure_speech.get_transcription_status(transcription_name, azure_subscription_key)
        transcript = ''
        if status == 'Succeeded':
            result_url = azure_speech.get_transcription_result_url(transcription_name, azure_subscription_key)
            download_file_name = result_url[result_url.rfind('/') + 1:]
            azure_speech.download_blob(azure_connection_string, azure_container_name, download_file_name, download_file_name)
            transcript = azure_speech.get_transcript_from_file(download_file_name)
        
        json_response = json.dumps({'status': status, 'transcript': transcript}, ensure_ascii=False)
        self.write(json_response)

if __name__ == "__main__":
    # AWS
    s3_bucket_name = os.environ.get('S3_BUCKET_NAME', 's3_bucket_name')

    # GCP
    gcs_bucket_name = os.environ.get('GCS_BUCKET_NAME', 'gcs_bucket_name')
    gcp_api_key = os.environ.get('GCP_API_KEY', 'gcp_api_key')
    credential_path = os.path.join(os.path.dirname(__file__), '../credentials/GOOGLE_APPLICATION_CREDENTIALS.json')
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credential_path

    # Azure
    azure_storage_account = os.environ['AZURE_STORAGE_ACCOUNT']
    azure_connection_string = os.environ['AZURE_STORAGE_CONNECTION_STRING']
    azure_container_name = os.environ['AZURE_STORAGE_CONTAINER_NAME']
    azure_subscription_key = os.environ['AZURE_SUBSCRIPTION_KEY']
    azure_service_sas_url = os.environ['AZURE_SERVICE_SAS_URL']

    application = tornado.web.Application(
        [
            url(r"/api/text", TextHandler, name='text'),
            url(r"/api/aws/upload", AwsUploadHandler, name='aws_upload'),
            url(r"/api/aws/recognize", AwsRecognizeHandler, name='aws_recognize'),
            url(r"/api/aws/text", AwsTextHandler, name='aws_text'),
            url(r"/api/gcp/upload", GcpUploadHandler, name='gcp_upload'),
            url(r"/api/gcp/recognize", GcpRecognizeHandler, name='gcp_recognize'),
            url(r"/api/gcp/text", GcpTextHandler, name='gcp_text'),
            url(r"/api/azure/upload", AzureUploadHandler, name='azure_upload'),
            url(r"/api/azure/recognize", AzureRecognizeHandler, name='azure_recognize'),
            url(r"/api/azure/text", AzureTextHandler, name='azure_text'),
        ],
    )
    server = tornado.httpserver.HTTPServer(application)
    server.listen(8080)
    tornado.ioloop.IOLoop.instance().start()