#!/usr/bin/env python3
"""
Complete script to:
1. Call FaceFusion analyze API to extract faces from image
2. Save face images as PNG files
3. Use extracted faces for multi-face image swapping
"""

import requests
import base64
import os
from datetime import datetime
import time
import random
import json

# Step 1: Analyze API 参数
ANALYZE_API_URL = "http://ec2-18-237-35-34.us-west-2.compute.amazonaws.com:8288/api/v1/analyze"
TARGET_PATH = "s3://facefusiondemo/images/source02.png"
FRAME_NUMBER = 0  # 对于图像，frame_number 通常为 0
OUTPUT_DIR = "./extracted_faces_images"

# Step 2: Face Swapping API 参数
HEADLESS_API_URL = "http://ec2-18-237-35-34.us-west-2.compute.amazonaws.com:8288/api/v1/headless-run"
# 可用的源图像路径（根据检测到的人脸数量动态选择）
AVAILABLE_SOURCE_PATHS = [
    "/home/ubuntu/facefusion/musk.jpg",
    "s3://facefusiondemo/input/source02.jpeg"
]
OUTPUT_PATH = "s3://facefusiondemo/output/image_result.png"
TARGET_IMAGE_PATH = "s3://facefusiondemo/images/source02.png"

def create_debug_faces_mapping(filtered_faces_mapping):
    """创建包含调试信息的人脸映射文件"""
    debug_mapping = {}

    for key, base64_data in filtered_faces_mapping.items():
        debug_mapping[key] = {
            "base64_data": base64_data,
            "debug_info": {
                "source_index": key,
                "timestamp": datetime.now().isoformat(),
                "enable_similarity_debug": True
            }
        }

    # 保存调试映射到文件
    debug_file_path = "./debug_faces_mapping_images.json"
    with open(debug_file_path, 'w') as f:
        json.dump(debug_mapping, f, indent=2)

    print(f"调试人脸映射已保存到: {debug_file_path}")
    return debug_file_path

def analyze_faces():
    """Step 1: 分析图像并提取人脸"""
    print("=" * 60)
    print("Step 1: 调用 FaceFusion Analyze API 提取图像人脸")
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
        response = requests.post(ANALYZE_API_URL, headers=headers, json=payload, timeout=120)
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
    """Step 2: 使用提取的人脸进行多人图像换脸"""
    print("\n" + "=" * 60)
    print("Step 2: 调用 FaceFusion Headless-Run API 进行多人图像换脸")
    print("=" * 60)

    # 根据检测到的人脸数量和可用源图像数量动态选择
    face_count = len(faces_mapping)
    available_source_count = len(AVAILABLE_SOURCE_PATHS)

    print(f"检测到 {face_count} 张人脸，可用源图像 {available_source_count} 张")
    print(f"Target path: {TARGET_IMAGE_PATH}")
    print(f"Output path: {OUTPUT_PATH}")
    print(f"检测到的人脸ID: {list(faces_mapping.keys())}")

    # 根据人脸数量和源图像数量的关系决定处理策略
    if face_count <= available_source_count:
        # 人脸数量不超过源图像数量，使用所有检测到的人脸
        source_paths = AVAILABLE_SOURCE_PATHS[:face_count]
        filtered_faces_mapping = faces_mapping
        print(f"使用所有 {face_count} 张检测到的人脸")
    else:
        # 人脸数量超过源图像数量，随机选择人脸进行映射
        source_paths = AVAILABLE_SOURCE_PATHS  # 使用所有可用的源图像

        # 从检测到的人脸中随机选择与源图像数量相等的人脸
        detected_face_ids = list(faces_mapping.keys())
        selected_face_ids = random.sample(detected_face_ids, available_source_count)

        # 创建新的映射，保持清晰的对应关系
        filtered_faces_mapping = {}
        for i, face_id in enumerate(selected_face_ids):
            filtered_faces_mapping[str(i)] = faces_mapping[face_id]

        print(f"人脸数量({face_count})超过源图像数量({available_source_count})")
        print(f"随机选择的原图像人脸ID: {selected_face_ids}")

        # 打印清晰的映射关系
        print("\n=== 详细人脸映射信息 ===")
        print("映射逻辑：源图像[新索引] -> 原图像人脸[原始ID]")
        for i, face_id in enumerate(selected_face_ids):
            base64_preview = faces_mapping[face_id][:50] + "..." if len(faces_mapping[face_id]) > 50 else faces_mapping[face_id]
            print(f"源图像[{i}] ({source_paths[i]}) -> 原图像人脸[{face_id}] (base64: {base64_preview})")

        print(f"\n最终API映射键值: {list(filtered_faces_mapping.keys())} (对应原图像人脸: {selected_face_ids})")

    print(f"使用的源图像路径: {source_paths}")
    print(f"最终人脸映射: {list(filtered_faces_mapping.keys())}")

    # 创建调试人脸映射文件（可选）
    # debug_file_path = create_debug_faces_mapping(filtered_faces_mapping)

    # 准备换脸请求 - 使用降低的阈值
    payload = {
        "source_paths": source_paths,
        "output_path": OUTPUT_PATH,
        "target_path": TARGET_IMAGE_PATH,
        "processors": ["face_swapper"],
        "face_selector_mode": "reference",
        "faces_mapping": filtered_faces_mapping,
        "reference_face_distance": 0.35
    }

    # 打印完整的请求信息用于调试
    print("\n=== API 请求详情 ===")
    print(f"API URL: {HEADLESS_API_URL}")
    print(f"Source paths: {payload['source_paths']}")
    print(f"Target path: {payload['target_path']}")
    print(f"Output path: {payload['output_path']}")
    print(f"Face selector mode: {payload['face_selector_mode']}")
    print(f"Reference face distance: {payload['reference_face_distance']}")
    print(f"Faces mapping keys: {list(payload['faces_mapping'].keys())}")

    # 打印每个人脸映射的base64数据长度
    for key, base64_data in payload['faces_mapping'].items():
        print(f"  映射[{key}]: base64长度={len(base64_data)}, 预览={base64_data[:30]}...")

    headers = {
        "Content-Type": "application/json"
    }

    try:
        # 调用换脸API
        print("正在提交图像换脸请求...")
        print("⚠️  多人脸图像换脸处理时间相对较短...")
        print(f"⏱️  超时设置: 120秒 (2分钟)")
        print(f"🖼️  目标图像: {TARGET_IMAGE_PATH}")
        print(f"📊 处理参数: {len(source_paths)}个源图像, 阈值={payload['reference_face_distance']}")

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
    """主函数：执行完整的图像人脸分析和换脸流程"""
    print("FaceFusion 多人图像换脸完整测试流程")
    print("包含：图像人脸分析 -> 保存人脸图像 -> 多人图像换脸")

    # Step 1: 分析并提取人脸
    encoded_faces = analyze_faces()
    if not encoded_faces:
        print("图像人脸分析失败，无法继续")
        return

    # Step 2: 使用提取的人脸进行换脸
    # 注意：这里使用从analyze API获取的真实base64数据
    face_swap_result = face_swap(encoded_faces)

    if face_swap_result:
        print("\n" + "=" * 60)
        print("✅ 完整流程执行成功!")
        print("=" * 60)
        print(f"1. 已提取并保存 {len(encoded_faces)} 张人脸图像")
        print(f"2. 已提交多人图像换脸请求")
        print(f"3. 输出图像将保存到: {OUTPUT_PATH}")
    else:
        print("\n" + "=" * 60)
        print("❌ 换脸步骤失败")
        print("=" * 60)

if __name__ == "__main__":
    main()
