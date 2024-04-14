import uuid
import boto3
import os
from datetime import datetime

class ModelClient:
    def __init__(self, model_id):
        self.model_id = model_id
        self.dynamodb = boto3.resource('dynamodb')
        self.s3 = boto3.client('s3')

    def submit_job(self, user_id, source_video_s3_path, swap_face_image_s3_path, output_video_s3_path):
        job_id = f"{uuid.uuid4().hex}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        output_video_name = f"{job_id}.mp4"

        # 触发调用 SageMaker endpoint
        # 此处省略调用 SageMaker 的代码

        # 将数据写入 DynamoDB 的 job_trace 表
        table = self.dynamodb.Table('job_trace')
        table.put_item(
            Item={
                'job_id': job_id,
                'user_id': user_id,
                'output_video_s3_path': output_video_s3_path + '/' + output_video_name
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
            if self.s3.head_object(Bucket=os.path.dirname(output_video_s3_path), Key=os.path.basename(output_video_s3_path)):
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
            else:
                return 'not finished'
        else:
            return 'not found job id: '+job_id

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
            self.s3.download_file(os.path.dirname(output_video_s3_path), os.path.basename(output_video_s3_path), local_file_path)
            with open(local_file_path, 'rb') as f:
                video_binary = f.read()
            os.remove(local_file_path)
            return video_binary
        else:
            return None
