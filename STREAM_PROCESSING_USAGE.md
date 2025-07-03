# FaceFusion 实时流媒体换脸功能使用指南

## 概述

FaceFusion 现在支持实时流媒体换脸功能，可以处理 RTMP、WebSocket、HTTP 等协议的实时视频流，并进行实时人脸替换。该功能采用异步处理架构，支持高并发和低延迟处理。

## 功能特性

- ✅ 支持多种流媒体协议：RTMP、RTMPS、WebSocket、HTTP/HTTPS
- ✅ 实时视频流分割和处理
- ✅ 异步多线程并行处理
- ✅ 单人换脸优化（专门针对单人场景）
- ✅ WebSocket 实时输出
- ✅ 自动资源管理和清理
- ✅ 处理统计和监控

## 架构组件

### 1. StreamSplitter (流分割器)
- 使用 FFmpeg 将输入流分割成固定时长的视频片段
- 支持多种流媒体协议
- 自动处理时间戳和格式转换

### 2. AsyncFaceProcessor (异步换脸处理器)
- 多线程并行处理视频片段
- 基于 FaceFusion 核心换脸算法
- 支持批量处理和错误恢复

### 3. StreamProcessor (流处理器)
- 协调分割器和处理器
- 管理处理队列和输出流
- 提供统计信息和状态监控

## API 接口

### 1. 启动流处理

```http
POST /api/v1/stream/start
Content-Type: application/json

{
    "stream_url": "rtmp://live.example.com/stream/key",
    "source_face_path": "/path/to/source/face.jpg",
    "segment_duration": 5.0,
    "max_workers": 4,
    "face_detector_model": "yolo_face",
    "face_detector_score": 0.5,
    "output_quality": 80
}
```

响应：
```json
{
    "success": true,
    "session_id": "uuid-session-id",
    "message": "Stream processing started successfully",
    "websocket_url": "/api/v1/stream/ws/uuid-session-id"
}
```

### 2. 获取处理状态

```http
GET /api/v1/stream/status/{session_id}
```

响应：
```json
{
    "session_id": "uuid-session-id",
    "status": "active",
    "message": "Stream processing active",
    "segments_processed": 25,
    "processing_fps": 2.3
}
```

### 3. 停止流处理

```http
POST /api/v1/stream/stop/{session_id}
```

### 4. WebSocket 接收处理结果

```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/stream/ws/uuid-session-id');

ws.onmessage = function(event) {
    if (event.data instanceof Blob) {
        // 处理后的视频片段数据
        const videoBlob = event.data;
        // 可以创建 video 元素播放或保存
    } else {
        // 元数据或状态信息
        const data = JSON.parse(event.data);
        console.log('Metadata:', data);
    }
};
```

## 使用示例

### Python 客户端示例

```python
import asyncio
import aiohttp
import websockets
import json

async def process_stream():
    # 1. 启动流处理
    async with aiohttp.ClientSession() as session:
        request_data = {
            "stream_url": "rtmp://your-stream-url",
            "source_face_path": "/path/to/source/face.jpg",
            "segment_duration": 5.0,
            "max_workers": 4
        }
        
        async with session.post(
            'http://localhost:8000/api/v1/stream/start',
            json=request_data
        ) as resp:
            result = await resp.json()
            session_id = result['session_id']
            print(f"Started session: {session_id}")
    
    # 2. 连接 WebSocket 接收处理结果
    ws_url = f"ws://localhost:8000/api/v1/stream/ws/{session_id}"
    
    async with websockets.connect(ws_url) as websocket:
        while True:
            try:
                message = await websocket.recv()
                
                if isinstance(message, bytes):
                    # 处理后的视频片段
                    print(f"Received video segment: {len(message)} bytes")
                    # 保存或处理视频数据
                    with open(f"segment_{int(time.time())}.mp4", "wb") as f:
                        f.write(message)
                else:
                    # 元数据
                    data = json.loads(message)
                    print(f"Metadata: {data}")
                    
            except websockets.exceptions.ConnectionClosed:
                break

# 运行
asyncio.run(process_stream())
```

### JavaScript 客户端示例

```javascript
async function startStreamProcessing() {
    // 启动流处理
    const response = await fetch('/api/v1/stream/start', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            stream_url: 'rtmp://your-stream-url',
            source_face_path: '/path/to/source/face.jpg',
            segment_duration: 5.0,
            max_workers: 4
        })
    });
    
    const result = await response.json();
    const sessionId = result.session_id;
    
    // 连接 WebSocket
    const ws = new WebSocket(`ws://localhost:8000/api/v1/stream/ws/${sessionId}`);
    
    ws.onmessage = function(event) {
        if (event.data instanceof Blob) {
            // 处理视频片段
            const videoUrl = URL.createObjectURL(event.data);
            const video = document.createElement('video');
            video.src = videoUrl;
            video.autoplay = true;
            document.body.appendChild(video);
        } else {
            // 处理元数据
            const data = JSON.parse(event.data);
            console.log('Segment metadata:', data);
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = function() {
        console.log('WebSocket connection closed');
    };
}
```

## 配置参数

### 流处理参数
- `stream_url`: 输入流 URL（必需）
- `source_face_path`: 源人脸图片路径（必需）
- `segment_duration`: 视频片段时长（秒，默认 5.0）
- `max_workers`: 最大工作线程数（默认 4）
- `output_quality`: 输出视频质量（1-100，默认 80）

### 人脸检测参数
- `face_detector_model`: 人脸检测模型（默认 "yolo_face"）
- `face_detector_score`: 检测阈值（0.0-1.0，默认 0.5）
- `face_selector_mode`: 人脸选择模式（默认 "reference"）
- `reference_face_distance`: 参考人脸距离（0.0-1.0，默认 0.3）

### 执行参数
- `execution_providers`: 执行提供者列表
- `execution_thread_count`: 执行线程数

## 性能优化建议

1. **硬件配置**
   - 使用 GPU 加速（CUDA/OpenCL）
   - 足够的内存（建议 8GB+）
   - 快速存储（SSD）

2. **参数调优**
   - 根据硬件性能调整 `max_workers`
   - 较短的 `segment_duration` 可降低延迟但增加开销
   - 适当降低 `output_quality` 可提高处理速度

3. **网络优化**
   - 确保稳定的网络连接
   - 使用 CDN 或就近部署
   - 考虑使用 UDP 协议减少延迟

## 故障排除

### 常见问题

1. **流连接失败**
   - 检查流 URL 是否正确
   - 确认网络连接和防火墙设置
   - 验证流协议支持

2. **处理速度慢**
   - 增加 `max_workers` 数量
   - 使用 GPU 加速
   - 降低输出质量

3. **内存不足**
   - 减少 `max_workers`
   - 缩短 `segment_duration`
   - 增加系统内存

4. **人脸检测失败**
   - 调整 `face_detector_score` 阈值
   - 确保源人脸图片质量
   - 检查目标流中是否有清晰人脸

### 日志和监控

- 查看 FaceFusion 日志获取详细错误信息
- 使用状态 API 监控处理进度
- 监控系统资源使用情况

## 限制和注意事项

1. **单人换脸限制**：当前版本专门优化用于单人换脸场景
2. **实时性要求**：处理速度取决于硬件性能和视频复杂度
3. **资源消耗**：实时处理需要大量 CPU/GPU 和内存资源
4. **网络依赖**：需要稳定的网络连接用于流输入和输出

## 未来改进

- [ ] 多人换脸支持
- [ ] 更多流媒体协议支持
- [ ] 自适应质量调整
- [ ] 分布式处理支持
- [ ] 更好的错误恢复机制
