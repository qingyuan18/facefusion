####  调用SageMaker endpoint 封装接口 #########
import uuid
import boto3
import os
from datetime import datetime
import json
import base64

runtime_sm_client = boto3.client(service_name="sagemaker-runtime")


class BytesEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        return super().default(obj)

class ModelClient:
    sagemaker_endpoint = ""
    def __init__(self, model_id):
        self.model_id = model_id
        self.dynamodb = boto3.resource('dynamodb')
        self.s3 = boto3.client('s3')

    def get_bucket_and_key(self,s3uri):
        pos = s3uri.find('/', 5)
        bucket = s3uri[5 : pos]
        key = s3uri[pos + 1 : ]
        return bucket, key


    def set_endpoint(self, sagemaker_endpoint):
        self.sagemaker_endpoint = sagemaker_endpoint

    def invoke_endpoint(self,request:str,content_type: str = "application/json"):
        content_type = content_type or "application/json"
        request_body = request
        payload = json.dumps(request_body)
        print(payload)
        global runtime_sm_client
        response = runtime_sm_client.invoke_endpoint(
            EndpointName=self.sagemaker_endpoint,
            ContentType=content_type,
            Body=payload,
        )
        result = response['Body'].read().decode()
        print('返回：',result)


    def analyze_video(self, user_id, source_video_s3_path, frame_number):
        job_id = f"{uuid.uuid4().hex}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 触发调用 SageMaker endpoint
        inputs = ['-t',source_video_s3_path,
                  '--execution-providers','cuda',
                  '--analyze_index',frame_number,
                  '--headless']
        request = {
        	        "method":"analyze",
        	        "input":inputs,
                    }
        response = self.invoke_endpoint(request,content_type="application/json")
        return response['Body'].read().decode("UTF-8")





    def submit_job(self, user_id, source_video_s3_path, swap_face_image_s3_path, output_video_s3_dir,faces_mapping_dict):
        job_id = f"{uuid.uuid4().hex}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        output_video_name = f"{job_id}.mp4"
        output_video_s3_path = output_video_s3_dir+"/"+output_video_name

        # 触发调用 SageMaker endpoint
        inputs = ['-s',swap_face_image_s3_path,'-t',source_video_s3_path,
                  '--execution-providers','cuda',
                  '-o','/opt/program/output/'+output_video_name,'-u',output_video_s3_path,'--headless']
        if faces_mapping_dict:
            s3_client = boto3.client('s3')
            temp_file_path = f"/tmp/{job_id}_faces_mapping.json"
            with open(temp_file_path, 'w') as f:
                json.dump(faces_mapping_dict, f, cls=BytesEncoder)
            # 上传文件到 S3
            faces_mapping_s3_key = f"{output_video_s3_dir}/{job_id}_faces_mapping.json"
            s3_bucket, key = self.get_bucket_and_key(faces_mapping_s3_key)
            s3_client.upload_file(temp_file_path, s3_bucket, key)
            # 参数传 face mapping的s3路径
            inputs.append(['--many',faces_mapping_s3_key)
            inputs.append(['--face-selector-mode','reference'])
        request = {
        	        "method":"submit",
        	        "input":inputs,
                    }
        self.invoke_endpoint(request)


        # 将数据写入 DynamoDB 的 job_trace 表
        table = self.dynamodb.Table('job_trace')
        table.put_item(
            Item={
                'job_id': job_id,
                'user_id': user_id,
                'output_video_s3_path': output_video_s3_path
            }
        )
        return job_id

    def get_status(self, user_id, job_id):
        table = self.dynamodb.Table('job_trace')
        response = table.get_item(
            Key={
                'job_id': job_id
            }
        )

        if 'Item' in response:
            output_video_s3_path = response['Item']['output_video_s3_path']
            bucket, key = self.get_bucket_and_key(output_video_s3_path)
            try:
                self.s3.head_object(Bucket=bucket, Key=key)
                table.update_item(
                    Key={
                        'job_id': job_id
                    },
                    UpdateExpression='SET #status = :status',
                    ExpressionAttributeNames={
                        '#status': 'status'
                    },
                    ExpressionAttributeValues={
                        ':status': 'success'
                    }
                )
                return 'success'
            except self.s3.exceptions.ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # 如果找不到对象，说明任务还未完成
                    return 'not finished'
                else:
                    # 其他错误，你可以根据需要进行处理或记录
                    print("Unexpected error: %s" % e)
                    return 'error'
        else:
            return 'not found job id: ' + job_id

    def get_result(self, job_id):
        table = self.dynamodb.Table('job_trace')
        response = table.get_item(
            Key={
                'job_id': job_id
            }
        )

        if 'Item' in response:
            output_video_s3_path = response['Item']['output_video_s3_path']
            local_file_path = f"/tmp/{os.path.basename(output_video_s3_path)}"
            bucket,key = self.get_bucket_and_key(output_video_s3_path)
            self.s3.download_file(bucket, key, local_file_path)
            with open(local_file_path, 'rb') as f:
                video_binary = f.read()
            os.remove(local_file_path)
            return video_binary
        else:
            return None
