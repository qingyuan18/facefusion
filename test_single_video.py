#!/usr/bin/env python3
"""
Simple script for single-person video face swapping with enhancement:
1. Use FaceFusion API for single face swapping
2. Apply both face_swapper and face_enhancer processors
3. Process the same video as multi-face test but with single source
"""

import requests
import json
from datetime import datetime

# API 配置
HEADLESS_API_URL = "http://ec2-18-237-35-34.us-west-2.compute.amazonaws.com:8288/api/v1/headless-run"

# 输入输出配置
SOURCE_PATH = "/home/ubuntu/facefusion/musk.jpg"  # 单个源图像
TARGET_VIDEO_PATH = "s3://facefusiondemo/videos/3faces_video01.mp4"  # 与多人换脸测试相同的视频
OUTPUT_PATH = "s3://facefusiondemo/output/single_video_enhanced.mp4"

def single_face_swap_with_enhancement():
    """执行单人视频换脸并增强"""
    print("=" * 60)
    print("FaceFusion 单人视频换脸 + 人脸增强测试")
    print("=" * 60)
    print(f"源图像: {SOURCE_PATH}")
    print(f"目标视频: {TARGET_VIDEO_PATH}")
    print(f"输出路径: {OUTPUT_PATH}")
    print(f"处理器: face_swapper + face_enhancer")

    # 准备API请求
    payload = {
        "source_paths": [SOURCE_PATH],
        "target_path": TARGET_VIDEO_PATH,
        "output_path": OUTPUT_PATH,
        "processors": ["face_swapper", "face_enhancer"],
        "face_selector_mode": "one",
        # Face swapper 参数
        "face_swapper_model": "inswapper_128_fp16",
        "face_swapper_pixel_boost": "512x512",
        # Face enhancer 参数
        "face_enhancer_model": "gfpgan_1.4",
        "face_enhancer_blend": 80,
        "face_enhancer_weight": 1.0,
        # 其他参数
        "execution_providers": ["cuda"]
    }

    headers = {
        "Content-Type": "application/json"
    }

    # 打印请求详情
    print("\n=== API 请求详情 ===")
    print(f"API URL: {HEADLESS_API_URL}")
    print(f"Source paths: {payload['source_paths']}")
    print(f"Target path: {payload['target_path']}")
    print(f"Output path: {payload['output_path']}")
    print(f"Processors: {payload['processors']}")
    print(f"Face selector mode: {payload['face_selector_mode']}")
    print(f"Face swapper model: {payload['face_swapper_model']}")
    print(f"Face enhancer model: {payload['face_enhancer_model']}")
    print(f"Face enhancer blend: {payload['face_enhancer_blend']}%")

    try:
        # 调用API
        print("\n正在提交单人换脸请求...")
        print("⚠️  单人换脸 + 增强处理时间较长，请耐心等待...")
        print(f"⏱️  超时设置: 600秒 (10分钟)")
        print(f"🎬 目标视频: {TARGET_VIDEO_PATH}")
        print(f"📊 处理参数: 1个源图像, face_swapper + face_enhancer")

        response = requests.post(HEADLESS_API_URL, headers=headers, json=payload, timeout=600)
        response.raise_for_status()
        result = response.json()

        print(f"\n换脸请求提交成功!")
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


def test_alternative_source():
    """测试使用S3源图像的版本"""
    print("\n" + "=" * 60)
    print("测试备用源图像 (S3路径)")
    print("=" * 60)
    
    # 使用S3路径的源图像
    alternative_source = "s3://facefusiondemo/input/source02.jpeg"
    alternative_output = "s3://facefusiondemo/output/single_video_enhanced_alt.mp4"
    
    print(f"备用源图像: {alternative_source}")
    print(f"备用输出路径: {alternative_output}")

    payload = {
        "source_paths": [alternative_source],
        "target_path": TARGET_VIDEO_PATH,
        "output_path": alternative_output,
        "processors": ["face_swapper", "face_enhancer"],
        "face_selector_mode": "one",
        "face_swapper_model": "inswapper_128_fp16",
        "face_swapper_pixel_boost": "512x512",
        "face_enhancer_model": "gfpgan_1.4",
        "face_enhancer_blend": 80,
        "face_enhancer_weight": 1.0,
        "execution_providers": ["cuda"]
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        print("正在提交备用源图像换脸请求...")
        response = requests.post(HEADLESS_API_URL, headers=headers, json=payload, timeout=600)
        response.raise_for_status()
        result = response.json()

        print(f"备用源图像换脸请求提交成功!")
        print(f"响应: {result}")

        job_id = result.get('job_id')
        if job_id:
            print(f"Job ID: {job_id}")

        return result

    except requests.exceptions.RequestException as e:
        print(f"备用源图像API请求错误: {e}")
        return None
    except Exception as e:
        print(f"备用源图像处理过程中出错: {e}")
        return None


def main():
    """主函数：执行单人视频换脸测试"""
    print("FaceFusion 单人视频换脸 + 增强完整测试")
    print("使用与多人换脸测试相同的目标视频")
    print("处理器: face_swapper + face_enhancer")
    
    # 测试主要源图像
    result1 = single_face_swap_with_enhancement()
    
    # 可选：测试备用源图像
    print("\n" + "=" * 80)
    user_input = input("是否要测试备用源图像? (y/n): ").strip().lower()
    if user_input in ['y', 'yes']:
        result2 = test_alternative_source()
    else:
        result2 = None
        print("跳过备用源图像测试")

    # 总结结果
    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    
    if result1:
        print("✅ 主要源图像换脸测试成功")
        print(f"   输出: {OUTPUT_PATH}")
    else:
        print("❌ 主要源图像换脸测试失败")
    
    if result2:
        print("✅ 备用源图像换脸测试成功")
        print(f"   输出: s3://facefusiondemo/output/single_video_enhanced_alt.mp4")
    elif user_input in ['y', 'yes']:
        print("❌ 备用源图像换脸测试失败")
    
    print("\n处理器配置:")
    print("- face_swapper: inswapper_128_fp16 模型")
    print("- face_enhancer: gfpgan_1.4 模型, 80% 混合度")
    print("- face_selector_mode: one (替换检测到的第一个人脸)")
    print("- 执行提供者: GPU")


if __name__ == "__main__":
    main()
