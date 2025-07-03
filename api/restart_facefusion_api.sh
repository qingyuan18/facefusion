#!/bin/bash

# 查找使用 7861 端口的进程
PID=$(lsof -ti:8288)

# 如果找到进程，则杀掉它
if [ ! -z "$PID" ]; then
    echo "Killing process $PID using port 8288"
    kill -9 $PID
else
    echo "No process found using port 8288"
fi


# 清空 nohup.out 文件
> nohup.out

nohup python ./main.py run &