#!/usr/bin/env python3
"""
视频流换脸测试数据源脚本
提供多种类型的测试流媒体源
"""

import asyncio
import aiohttp
import websockets
import json
import time
import os
import subprocess
import tempfile
from pathlib import Path

# API 配置
API_URL = "http://ec2-18-237-35-34.us-west-2.compute.amazonaws.com:8288"
SOURCE_FACE = "/home/ubuntu/facefusion/musk.jpg"  # 修改为实际路径

# 测试流媒体源
TEST_STREAMS = {
    "http_video": {
        "name": "HTTP视频流",
        "url": "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
        "description": "标准HTTP视频文件，适合基础测试"
    },
    "big_buck_bunny": {
        "name": "Big Buck Bunny",
        "url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "description": "高质量测试视频，包含清晰人脸"
    },
    "short_test": {
        "name": "短视频测试",
        "url": "https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4",
        "description": "10秒短视频，快速测试"
    },
    "hls_stream": {
        "name": "HLS直播流",
        "url": "https://bitdash-a.akamaihd.net/content/sintel/hls/playlist.m3u8",
        "description": "HLS格式直播流"
    }
}

def create_local_rtmp_server():
    """创建本地RTMP服务器用于测试"""
    print("🔧 创建本地RTMP服务器...")
    
    # 使用FFmpeg创建本地RTMP流
    rtmp_command = [
        "ffmpeg",
        "-re",  # 实时播放
        "-i", "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
        "-c", "copy",
        "-f", "flv",
        "rtmp://localhost/live/test"
    ]
    
    try:
        # 检查FFmpeg是否可用
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg可用，可以创建本地RTMP流")
        print("💡 运行命令创建RTMP流:")
        print(f"   {' '.join(rtmp_command)}")
        return "rtmp://localhost/live/test"
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg不可用，无法创建本地RTMP流")
        return None

def create_webcam_stream():
    """创建摄像头流用于测试"""
    print("📹 创建摄像头流...")
    
    # 检查是否有摄像头设备
    webcam_command = [
        "ffmpeg",
        "-f", "avfoundation",  # macOS
        "-i", "0",  # 默认摄像头
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-f", "flv",
        "rtmp://localhost/live/webcam"
    ]
    
    try:
        print("💡 运行命令创建摄像头流:")
        print(f"   {' '.join(webcam_command)}")
        return "rtmp://localhost/live/webcam"
    except Exception as e:
        print(f"❌ 无法创建摄像头流: {e}")
        return None

async def test_stream_availability(stream_url):
    """测试流媒体源是否可用"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(stream_url, timeout=10) as response:
                return response.status == 200
    except:
        return False

async def test_stream_processing(stream_name, stream_url):
    """测试特定流媒体源的换脸处理"""
    print(f"\n🎬 测试流媒体源: {stream_name}")
    print(f"📡 URL: {stream_url}")
    
    # 检查源人脸文件
    if not os.path.exists(SOURCE_FACE):
        print(f"❌ 源人脸文件不存在: {SOURCE_FACE}")
        return False
    
    session_id = None
    
    try:
        # 1. 启动流式处理
        request_data = {
            "stream_url": stream_url,
            "source_face_path": SOURCE_FACE,
            "segment_duration": 3.0,
            "max_workers": 2,
            "output_quality": 70,
            "face_detector_model": "yolo_face",
            "face_selector_mode": "one",  # 单人换脸
            "execution_providers": ["cuda"]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_URL}/api/v1/stream/start',
                json=request_data,
                timeout=30
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('success'):
                        session_id = result['session_id']
                        print(f"✅ 启动成功! 会话ID: {session_id}")
                    else:
                        print(f"❌ 启动失败: {result.get('message')}")
                        return False
                else:
                    error = await resp.text()
                    print(f"❌ HTTP错误 {resp.status}: {error}")
                    return False
        
        # 2. 等待处理开始
        await asyncio.sleep(5)
        
        # 3. 连接WebSocket接收结果
        ws_url = f"ws://{API_URL.split('//')[1]}/api/v1/stream/ws/{session_id}"
        
        segment_count = 0
        max_segments = 2  # 只测试2个片段
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接成功")
            
            while segment_count < max_segments:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    
                    if isinstance(message, bytes):
                        segment_count += 1
                        filename = f"stream_test_{stream_name}_{segment_count}.mp4"
                        
                        with open(filename, "wb") as f:
                            f.write(message)
                        
                        print(f"📹 保存片段: {filename} ({len(message)} bytes)")
                        
                    else:
                        try:
                            data = json.loads(message)
                            msg_type = data.get('type', 'unknown')
                            if msg_type == 'status':
                                print(f"📡 {data.get('message')}")
                            elif msg_type == 'error':
                                print(f"❌ 错误: {data.get('message')}")
                        except:
                            print(f"📨 收到消息: {message}")
                            
                except asyncio.TimeoutError:
                    print("⏰ 等待超时")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 连接已关闭")
                    break
        
        print(f"✅ 成功处理 {segment_count} 个片段")
        return segment_count > 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False
        
    finally:
        # 停止流式处理
        if session_id:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f'{API_URL}/api/v1/stream/stop/{session_id}') as resp:
                        if resp.status == 200:
                            print("✅ 流式处理已停止")
            except Exception as e:
                print(f"❌ 停止时发生错误: {e}")

async def main():
    """主测试函数"""
    print("🎬 FaceFusion 视频流换脸测试")
    print("=" * 60)
    
    # 检查API服务器
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_URL}/api/v1/health', timeout=10) as resp:
                if resp.status == 200:
                    print("✅ FaceFusion API服务器可用")
                else:
                    print("❌ FaceFusion API服务器不可用")
                    return
    except Exception as e:
        print(f"❌ 无法连接到API服务器: {e}")
        return
    
    # 测试流媒体源可用性
    print("\n📡 检查流媒体源可用性...")
    available_streams = []
    
    for stream_id, stream_info in TEST_STREAMS.items():
        print(f"检查 {stream_info['name']}...")
        is_available = await test_stream_availability(stream_info['url'])
        if is_available:
            print(f"✅ {stream_info['name']} 可用")
            available_streams.append((stream_id, stream_info))
        else:
            print(f"❌ {stream_info['name']} 不可用")
    
    if not available_streams:
        print("❌ 没有可用的流媒体源")
        return
    
    # 测试每个可用的流媒体源
    print(f"\n🧪 开始测试 {len(available_streams)} 个可用流媒体源...")
    
    results = []
    for stream_id, stream_info in available_streams:
        success = await test_stream_processing(stream_info['name'], stream_info['url'])
        results.append((stream_info['name'], success))
        
        # 等待一段时间再测试下一个
        if stream_id != available_streams[-1][0]:
            print("⏳ 等待5秒后测试下一个源...")
            await asyncio.sleep(5)
    
    # 显示结果
    print("\n" + "=" * 60)
    print("测试结果总结:")
    print("=" * 60)
    
    for stream_name, success in results:
        status = "✅ 成功" if success else "❌ 失败"
        print(f"{stream_name:20} : {status}")
    
    successful_tests = sum(1 for _, success in results if success)
    print(f"\n总计: {successful_tests}/{len(results)} 个流媒体源测试成功")
    
    # 提供额外建议
    print("\n💡 额外测试建议:")
    print("1. 本地RTMP服务器:")
    rtmp_url = create_local_rtmp_server()
    if rtmp_url:
        print(f"   使用: {rtmp_url}")
    
    print("2. 摄像头流:")
    webcam_url = create_webcam_stream()
    if webcam_url:
        print(f"   使用: {webcam_url}")
    
    print("3. 自定义流媒体源:")
    print("   修改 TEST_STREAMS 字典添加您的流媒体URL")

if __name__ == "__main__":
    print("请确保:")
    print("1. FaceFusion API服务器正在运行")
    print("2. 修改 SOURCE_FACE 路径为实际的人脸图片")
    print("3. 网络连接正常")
    print()
    
    asyncio.run(main())
