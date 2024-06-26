from typing import Tuple, Optional
import gradio
import os
from pathlib import Path
import boto3

import facefusion.globals
from facefusion import wording
from facefusion.core import limit_resources, conditional_process
from facefusion.uis.core import get_ui_component
from facefusion.utilities import is_image, is_video, normalize_output_path, clear_temp
from ModelClient import ModelClient

OUTPUT_IMAGE : Optional[gradio.Image] = None
OUTPUT_VIDEO : Optional[gradio.Video] = None
OUTPUT_START_BUTTON : Optional[gradio.Button] = None
OUTPUT_CLEAR_BUTTON : Optional[gradio.Button] = None
CHECKBOX: Optional[gradio.Checkbox] = None
TEXT_INPUT: Optional[gradio.Textbox] = None
CONFIRM_BUTTON: Optional[gradio.Button] = None
model_client = ModelClient("facefusion-v2.2")


def render() -> None:
	global OUTPUT_IMAGE
	global OUTPUT_VIDEO
	global OUTPUT_START_BUTTON
	global OUTPUT_CLEAR_BUTTON
	global CHECKBOX
    global TEXT_INPUT
    global CONFIRM_BUTTON

	OUTPUT_IMAGE = gradio.Image(
		label = wording.get('output_image_or_video_label'),
		visible = False
	)
	OUTPUT_VIDEO = gradio.Video(
		label = wording.get('output_image_or_video_label')
	)
	OUTPUT_START_BUTTON = gradio.Button(
		value = wording.get('start_button_label'),
		variant = 'primary',
		size = 'sm'
	)
	OUTPUT_CLEAR_BUTTON = gradio.Button(
		value = wording.get('clear_button_label'),
		size = 'sm'
	)
	CHECKBOX = gradio.Checkbox(
        label="Enable Custom Endpoint",
        value=False
    )
    TEXT_INPUT = gradio.Textbox(
        label="Custom Endpoint",
        disabled=True
    )
    BUCKET_NAME_INPUT = gradio.Textbox(
            label="Bucket Name",
            disabled=True
    )
    CONFIRM_BUTTON = gradio.Button(
        value="Confirm",
        size='sm'
    )


def toggle_text_input(checked):
    return gradio.Textbox(value="", disabled=not checked), gradio.Textbox(value="", disabled=not checked)

def confirm(endpoint):
    global  model_client
    if endpoint:
        model_client.set_endpoint(endpoint)
    facefusion.globals.output_video_s3_dir = f"s3://{bucket_name}/output/"

def listen() -> None:
	output_path_textbox = get_ui_component('output_path_textbox')
	if output_path_textbox:
		OUTPUT_START_BUTTON.click(start, inputs = output_path_textbox, outputs = [ OUTPUT_IMAGE, OUTPUT_VIDEO ])
	OUTPUT_CLEAR_BUTTON.click(clear, outputs = [ OUTPUT_IMAGE, OUTPUT_VIDEO ])
	CHECKBOX.change(toggle_text_input, inputs=CHECKBOX, outputs=[TEXT_INPUT,BUCKET_NAME_INPUT])
    CONFIRM_BUTTON.click(confirm, inputs=[TEXT_INPUT,BUCKET_NAME_INPUT])


def start(output_path : str) -> Tuple[gradio.Image, gradio.Video]:
	facefusion.globals.output_path = normalize_output_path(facefusion.globals.source_path, facefusion.globals.target_path, output_path)
	limit_resources()
	## TBD
	if CHECKBOX.value:
    # Upload input files to the specified S3 bucket
        s3_client = boto3.client('s3')
        bucket_name = BUCKET_NAME_INPUT.value
        source_key = f"input/{Path(facefusion.globals.source_path).name}"
        target_key = f"input/{Path(facefusion.globals.target_path).name}"
        s3_client.upload_file(facefusion.globals.source_path, bucket_name, source_key)
        s3_client.upload_file(facefusion.globals.target_path, bucket_name, target_key)
    # update source image and video path
        #facefusion.globals.source_path = f"s3://{bucket_name}/{source_key}"
        #facefusion.globals.target_path = f"s3://{bucket_name}/{target_key}"
    # submit to sagemaker by model Client
        job_id = model_client.submit_job("local_run",
                                        swap_face_image_s3_path=f"s3://{bucket_name}/{source_key}",
                                        source_video_s3_path=f"s3://{bucket_name}/{target_key}",
                                        output_video_s3_dir=facefusion.globals.output_video_s3_dir)
        try:
            while True:
                  status = client.get_status( "local_run", job_id)
                  if status == "success":
                      break
            response = client.get_result(job_id)
            #把response bytes写入facefusion.global.output_path的路径下
            output_dir = Path(facefusion.globals.output_path).parent
            os.makedirs(output_dir, exist_ok=True)
            with open(facefusion.globals.output_path, 'wb') as f:
                f.write(response)
        except Exception as e:
            print(f'{e} process failed!, please check sagemaker endpoint logs')

    else:
	    conditional_process()
	if is_image(facefusion.globals.output_path):
		return gradio.Image(value = facefusion.globals.output_path, visible = True), gradio.Video(value = None, visible = False)
	if is_video(facefusion.globals.output_path):
		return gradio.Image(value = None, visible = False), gradio.Video(value = facefusion.globals.output_path, visible = True)
	return gradio.Image(), gradio.Video()


def clear() -> Tuple[gradio.Image, gradio.Video]:
	if facefusion.globals.target_path:
		clear_temp(facefusion.globals.target_path)
	return gradio.Image(value = None), gradio.Video(value = None)
