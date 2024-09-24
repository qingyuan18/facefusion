#!/usr/bin/env python3

from facefusion import core
import sys
import os

if __name__ == '__main__':
    args = sys.argv[1:]

    # 检查是否包含 "--many" 参数
    many_index = -1
    # 检查是否包含 "--analyze" 参数
    analyze_index = -1
    for i, arg in enumerate(args):
        if arg == "--many":
            many_index = i
        if arg == "--analyze":
            analyze_index = i

    if many_index != -1 and many_index + 1 < len(args):
        # 设置环境变量 "faces_mapping"
        os.environ["faces_mapping"] = args[many_index + 1]
        # 从参数列表中移除 "--many" 及其值
        args = args[:many_index] + args[many_index+2:]

    if analyze_index != -1 and analyze_index + 1 < len(args):
        # 设置环境变量 "analyze_index"
        os.environ["analyze_index"] = args[analyze_index + 1]
        # 从参数列表中移除 "--analyze_index" 及其值
        args = args[:analyze_index] + args[analyze_index+2:]

    # 调用 core.cli 函数，传递修改后的参数
    core.cli(args)
