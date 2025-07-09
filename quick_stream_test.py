#!/usr/bin/env python3
"""
快速流式换脸测试脚本
"""

import asyncio
import aiohttp
import websockets
import json
import time
import os


async def quick_test():
    """快速测试流式换脸功能"""
    
    # 配置参数 - 请根据实际情况修改
    API_URL = "http://localhost:8288"
    STREAM_URL = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"  # 示例视频URL
    SOURCE_FACE = "/path/to/your/source_face.jpg"  # 请替换为实际的人脸图片路径
    
    print("🎬 快速流式换脸测试")
    print("=" * 40)
    
    # 检查源人脸文件
    if not os.path.exists(SOURCE_FACE):
        print(f"❌ 请先设置正确的源人脸图片路径: {SOURCE_FACE}")
        print("   修改脚本中的 SOURCE_FACE 变量")
        return
    
    session_id = None
    
    try:
        # 1. 启动流式处理
        print("🚀 启动流式处理...")
        
        request_data = {
            "stream_url": STREAM_URL,
            "source_face_path": SOURCE_FACE,
            "segment_duration": 3.0,  # 3秒片段
            "max_workers": 2,
            "output_quality": 70
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f'{API_URL}/api/v1/stream/start',
                json=request_data
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get('success'):
                        session_id = result['session_id']
                        print(f"✅ 启动成功! 会话ID: {session_id}")
                    else:
                        print(f"❌ 启动失败: {result.get('message')}")
                        return
                else:
                    error = await resp.text()
                    print(f"❌ HTTP错误 {resp.status}: {error}")
                    return
        
        # 2. 等待处理开始
        print("⏳ 等待处理开始...")
        await asyncio.sleep(3)
        
        # 3. 检查状态
        print("📊 检查处理状态...")
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{API_URL}/api/v1/stream/status/{session_id}') as resp:
                if resp.status == 200:
                    status = await resp.json()
                    print(f"   状态: {status.get('status')}")
                    print(f"   已处理片段: {status.get('segments_processed', 0)}")
                else:
                    print(f"❌ 获取状态失败: {resp.status}")
        
        # 4. 连接WebSocket接收结果
        print("🔌 连接WebSocket接收处理结果...")
        ws_url = f"ws://localhost:8288/api/v1/stream/ws/{session_id}"
        
        segment_count = 0
        max_segments = 3  # 只接收3个片段用于测试
        
        async with websockets.connect(ws_url) as websocket:
            print("✅ WebSocket连接成功，等待处理结果...")
            
            while segment_count < max_segments:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                    
                    if isinstance(message, bytes):
                        # 视频片段数据
                        segment_count += 1
                        filename = f"test_segment_{segment_count}.mp4"
                        
                        with open(filename, "wb") as f:
                            f.write(message)
                        
                        print(f"📹 保存片段 #{segment_count}: {filename} ({len(message)} bytes)")
                        
                    else:
                        # 元数据
                        try:
                            data = json.loads(message)
                            msg_type = data.get('type', 'unknown')
                            
                            if msg_type == 'status':
                                print(f"📡 {data.get('message')}")
                            elif msg_type == 'segment_metadata':
                                metadata = data.get('metadata', {})
                                print(f"📊 片段元数据: 处理时间={metadata.get('processing_time', 0):.2f}s")
                            elif msg_type == 'error':
                                print(f"❌ 错误: {data.get('message')}")
                        except:
                            print(f"📨 收到消息: {message}")
                            
                except asyncio.TimeoutError:
                    print("⏰ 等待超时，可能处理较慢...")
                    break
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 连接已关闭")
                    break
        
        print(f"✅ 成功接收 {segment_count} 个处理后的视频片段")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        
    finally:
        # 5. 停止流式处理
        if session_id:
            print("🛑 停止流式处理...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(f'{API_URL}/api/v1/stream/stop/{session_id}') as resp:
                        if resp.status == 200:
                            print("✅ 流式处理已停止")
                        else:
                            print(f"❌ 停止失败: {resp.status}")
            except Exception as e:
                print(f"❌ 停止时发生错误: {e}")
    
    print("🏁 测试完成")


if __name__ == "__main__":
    print("请确保:")
    print("1. FaceFusion API服务器正在运行 (http://localhost:8288)")
    print("2. 修改脚本中的 SOURCE_FACE 路径为实际的人脸图片")
    print("3. 网络连接正常")
    print()
    
    asyncio.run(quick_test())
