# This is the file that implements a flask server to do inferences. It's the file that you will modify to
# implement the scoring for your own algorithm.

from __future__ import print_function

import io
import json
import os
import sys
import flask
import subprocess
import threading
from facefusion import core
import boto3
from concurrent.futures import ThreadPoolExecutor
import uuid

# 创建一个线程池
executor = ThreadPoolExecutor(max_workers=5)

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
        #print(args)
        #result=core.cli(args)

        ## 后台执行
        task_id = str(uuid.uuid4())
        command = f"python run.py {' '.join(args)}"
        output_file = f"/tmp/{task_id}.out"
        error_file = f"/tmp/{task_id}.err"
        full_command = f"nohup {command} > {output_file} 2> {error_file} &"
        os.system(full_command)
        result = {"message": "Command executed in background"}


        ## 线程执行
        #future = executor.submit(core.cli, args)
        #result = {"message": "Command executed in background"}
    elif input_json['method']=="get_status":
        s3_ouput_path= input_json['input']
        # 使用 Boto3 检查输出目录是否有文件生成
        s3 = boto3.resource('s3')
        output_s3_path = input_json['input']
        bucket_name, key = get_bucket_and_key(output_s3_path)
        bucket = s3.Bucket(bucket_name)
        objects = list(bucket.objects.filter(Prefix=key))
        if objects:
            result = {"status": "success"}
        else:
            result = {"status": "processing"}
    else:
        result={"message":"not supported method"}

    # 返回结果
    print(json.dumps(result))

    return flask.Response(response=json.dumps(result), status=200, mimetype="application/json")


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
