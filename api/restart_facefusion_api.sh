#!/bin/bash

# 查找使用 8288 端口的进程
PID=$(lsof -ti:8288)

# 如果找到进程，则杀掉它
if [ ! -z "$PID" ]; then
    echo "Killing process $PID using port 8288"
    kill -9 $PID
else
    echo "No process found using port 8288"
fi

# 等待进程完全停止
sleep 2

# 清空 nohup.out 文件
> nohup.out

# 设置环境变量以禁用缓冲
export PYTHONUNBUFFERED=1
export PYTHONIOENCODING=utf-8

echo "Starting FaceFusion API service with real-time logging..."
echo "Logs will be written to nohup.out in real-time"

# 使用 stdbuf 禁用缓冲，并使用 tee 实现实时输出
nohup stdbuf -oL -eL python ./main.py run 2>&1 | tee -a nohup.out &

echo "API service started. PID: $!"
echo "Monitor logs with: tail -f nohup.out"
echo "Stop service with: kill $!"