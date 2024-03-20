# This is the file that implements a flask server to do inferences. It's the file that you will modify to
# implement the scoring for your own algorithm.

from __future__ import print_function

import io
import json
import os
import sys
import flask
import subprocess
from facefusion import core

#https://github.com/aws-samples/sagemaker-stablediffusion-quick-kit/blob/main/inference/sagemaker/byoc_sdxl/code/inference.py
prefix = "/opt/ml/"
model_path = os.path.join(prefix, "model")


def get_bucket_and_key(s3uri):
    pos = s3uri.find('/', 5)
    bucket = s3uri[5 : pos]
    key = s3uri[pos + 1 : ]
    return bucket, key


# The flask app for serving predictions
app = flask.Flask(__name__)



@app.route("/ping", methods=["GET"])
def ping():
    health=200
    status = 200 if health else 404
    return flask.Response(response="\n", status=status, mimetype="application/json")

@app.route("/invocations", methods=["POST"])
def transformation():
    # 获取命令行参数
    input_json = flask.request.get_json()
    if input_json['method']=="submit":
        args = input_json['input']
        print(args)
        result=core.cli(args)
    elif input_json['method']=="get_status":
        s3_ouput_path= input_json['input']
        # 使用 Boto3 检查输出目录是否有文件生成
        s3 = boto3.resource('s3')
        bucket_name, key = get_bucket_and_key(model_path)
        bucket = s3.Bucket(bucket_name)
        objects = list(bucket.objects.filter(Prefix=key))
        if objects:
            result = {"status": "success"}
        else:
            result = {"status": "processing"}
    elif input_json['method']=="get_result":
        # 返回 S3 路径
        s3_ouput_path= input_json['input']
        result = {
            "s3_output_path": s3_ouput_path
        }
    else：
        result={"message":"not supported method"}

    # 返回结果
    print(json.dumps(result))
    
    return flask.Response(response=result, status=200, mimetype="application/json")


















#     # 执行 run.py,并传递命令行参数
#     process = subprocess.Popen(['python', 'run.py'] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

#     # 获取输出
#     stdout, stderr = process.communicate()
#     print(stdout.decode())
#     # 检查是否有错误输出
#     if stderr:
#         print(f'Error: {stderr.decode()}')
#         return

#     # 获取返回的字符串
#     predictions = stdout.decode().strip()

#     # 将输出格式化为指定的格式
#     result = {'results': predictions}