#!/usr/bin/env python3
"""
Complete script to:
1. Call FaceFusion analyze API to extract faces
2. Save face images as PNG files
3. Use extracted faces for multi-face swapping
"""

import requests
import base64
import os
from datetime import datetime
import time

# Step 1: Analyze API 参数
ANALYZE_API_URL = "http://ec2-18-237-35-34.us-west-2.compute.amazonaws.com:8288/api/v1/analyze"
TARGET_PATH = "s3://facefusiondemo/41a13dad-99d1-4cf0-b9fb-58712fd10f70_WeChat_20240709163338.mp4"
FRAME_NUMBER = 80
OUTPUT_DIR = "./extracted_faces"

# Step 2: Face Swapping API 参数
HEADLESS_API_URL = "http://ec2-18-237-35-34.us-west-2.compute.amazonaws.com:8288/api/v1/headless-run"
# 可用的源图像路径（根据检测到的人脸数量动态选择）
AVAILABLE_SOURCE_PATHS = [
    "/home/ubuntu/facefusion/musk.jpg",
    "/home/ubuntu/facefusion/tangyan.jpg"
]
OUTPUT_PATH = "s3://facefusiondemo/output/video.mp4"
TARGET_VIDEO_PATH = "s3://facefusiondemo/41a13dad-99d1-4cf0-b9fb-58712fd10f70_WeChat_20240709163338.mp4"

def analyze_faces():
    """Step 1: 分析视频并提取人脸"""
    print("=" * 60)
    print("Step 1: 调用 FaceFusion Analyze API 提取人脸")
    print("=" * 60)
    print(f"Target: {TARGET_PATH}")
    print(f"Frame: {FRAME_NUMBER}")

    # 准备API请求
    payload = {
        "target_path": TARGET_PATH,
        "frame_number": FRAME_NUMBER
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 调用API
        response = requests.post(ANALYZE_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()

        # 检查API调用是否成功
        if not result.get('success', False):
            print(f"API调用失败: {result.get('message', 'Unknown error')}")
            return None

        print(f"API调用成功: {result.get('message', '')}")

        # 获取编码的人脸图像
        encoded_faces = result.get('encoded_faces', {})
        if not encoded_faces:
            print("未找到人脸")
            return None

        print(f"找到 {len(encoded_faces)} 张人脸")

        # 创建输出目录
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # 保存每张人脸图像
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_count = 0

        for face_id, base64_data in encoded_faces.items():
            try:
                # 解码base64数据
                image_data = base64.b64decode(base64_data)

                # 生成文件名
                filename = f"face_{face_id}_{timestamp}.png"
                filepath = os.path.join(OUTPUT_DIR, filename)

                # 保存图像
                with open(filepath, 'wb') as f:
                    f.write(image_data)

                print(f"已保存人脸 {face_id} 到: {filepath}")
                saved_count += 1

            except Exception as e:
                print(f"保存人脸 {face_id} 时出错: {e}")

        print(f"\n成功保存了 {saved_count} 张人脸图像到 {OUTPUT_DIR}")
        return encoded_faces

    except requests.exceptions.RequestException as e:
        print(f"API请求错误: {e}")
        return None
    except Exception as e:
        print(f"处理过程中出错: {e}")
        return None


def face_swap(faces_mapping):
    """Step 2: 使用提取的人脸进行多人换脸"""
    print("\n" + "=" * 60)
    print("Step 2: 调用 FaceFusion Headless-Run API 进行多人换脸")
    print("=" * 60)

    # 根据检测到的人脸数量动态选择源图像
    face_count = len(faces_mapping)
    source_paths = AVAILABLE_SOURCE_PATHS[:face_count]  # 只取需要的数量

    print(f"检测到 {face_count} 张人脸，使用 {len(source_paths)} 张源图像")
    print(f"Source paths: {source_paths}")
    print(f"Target path: {TARGET_VIDEO_PATH}")
    print(f"Output path: {OUTPUT_PATH}")
    print(f"Face mapping: {list(faces_mapping.keys())}")

    # 如果只有一张人脸，只使用第一张人脸的mapping
    if face_count == 1:
        # 只保留第一张人脸的mapping
        filtered_faces_mapping = {"0": faces_mapping.get("0", list(faces_mapping.values())[0])}
        print("单人脸模式：只使用第一张检测到的人脸")
    else:
        filtered_faces_mapping = faces_mapping
        print(f"多人脸模式：使用所有 {face_count} 张检测到的人脸")

    # 准备换脸请求
    payload = {
        "source_paths": source_paths,
        "output_path": OUTPUT_PATH,
        "target_path": TARGET_VIDEO_PATH,
        "processors": ["face_swapper"],
        "face_selector_mode": "reference",
        "faces_mapping": filtered_faces_mapping,
        "reference_face_distance": 0.6
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 调用换脸API
        print("正在提交换脸请求...")
        response = requests.post(HEADLESS_API_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()

        print(f"换脸请求提交成功!")
        print(f"响应: {result}")

        # 如果有job_id，可以用来跟踪处理状态
        job_id = result.get('job_id')
        if job_id:
            print(f"Job ID: {job_id}")
            print("您可以使用此Job ID来跟踪处理状态")

        return result

    except requests.exceptions.RequestException as e:
        print(f"换脸API请求错误: {e}")
        return None
    except Exception as e:
        print(f"换脸处理过程中出错: {e}")
        return None


def main():
    """主函数：执行完整的人脸分析和换脸流程"""
    print("FaceFusion 多人换脸完整测试流程")
    print("包含：人脸分析 -> 保存人脸图像 -> 多人换脸")

    # Step 1: 分析并提取人脸
    encoded_faces = analyze_faces()
    if not encoded_faces:
        print("人脸分析失败，无法继续")
        return

    # Step 2: 使用提取的人脸进行换脸
    # 注意：这里使用从analyze API获取的真实base64数据
    face_swap_result = face_swap(encoded_faces)

    if face_swap_result:
        print("\n" + "=" * 60)
        print("✅ 完整流程执行成功!")
        print("=" * 60)
        print(f"1. 已提取并保存 {len(encoded_faces)} 张人脸图像")
        print(f"2. 已提交多人换脸请求")
        print(f"3. 输出视频将保存到: {OUTPUT_PATH}")
    else:
        print("\n" + "=" * 60)
        print("❌ 换脸步骤失败")
        print("=" * 60)

if __name__ == "__main__":
    main()
