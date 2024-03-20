import subprocess
import sys
import json
from facefusion import core

def main():
    # 获取命令行参数
    args = sys.argv[1:]
    arg_list=['-s', 'taotao.jpeg', '-t', 'lht.jpg', '-o', '.', '--headless']
    print(arg_list)
    result=core.cli(arg_list)
    # 返回结果
    print(json.dumps(result))

if __name__ == '__main__':
    main()