# Build an image that can do training and inference in SageMaker
# This is a Python 3 image that uses the nginx, gunicorn, flask stack
# for serving inferences in a stable way.

# FROM pytorch/pytorch:2.1.0-cuda11.8-cudnn8-devel
# FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-cpu-py310-ubuntu20.04-ec2
# FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:2.1.0-gpu-py310-cu118-ubuntu20.04-ec2
# FROM 763104351884.dkr.ecr.us-east-1.amazonaws.com/pytorch-inference:1.13.1-gpu-py39-cu117-ubuntu20.04-ec2
# ref from https://github.com/facefusion/facefusion-docker
FROM python:3.10
ARG DEBIAN_FRONTEND=noninteractive
ARG FACEFUSION_VERSION=2.3.0
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/program:${PATH}"


WORKDIR /opt/program

RUN apt-get update
RUN apt-get install curl -y
RUN apt-get install ffmpeg -y

##安装sagemaker endpoint所需的组件
RUN apt-get install nginx -y  
RUN pip install --no-cache-dir boto3 flask gunicorn
# RUN git clone https://github.com/facefusion/facefusion.git --branch ${FACEFUSION_VERSION} --single-branch .
##拷贝包含sagemaker endpoint所需的python和配置文件
COPY facefusion /opt/program
# RUN pip install -r requirements.txt
RUN python install.py --torch cpu --onnxruntime default

WORKDIR /opt/program

