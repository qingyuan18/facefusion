# import io
# import json
# import os
# import sys
# import subprocess
# # 指定完整的文件路径
# file_path = './run.py'

# # 使用subprocess.run运行文件
# # result = subprocess.run(['python', file_path], capture_output=True, text=True)
# # result = subprocess.run(['python','run.py', '-s', 'image1.jpg', '-t', 'test.mp4','-o','.','--headless'])
# data = "python run.py -s image1.jpg -t test.mp4 -o . --headless"
# print(data)
# data.split()


# # result=subprocess.run(data, shell=True)
# result = subprocess.Popen(['python','run.py', '-s', '1.jpg', '-t', 'test.mp4','-o','.','--headless'], shell=True)
# print("end inference",result)
# # Return value
# resultjson = json.dumps(result.returncode)


import subprocess
import sys
import json
from facefusion import core
def main():
    # 获取命令行参数
    args = sys.argv[1:]
    args=['-s', 'lht.jpg', '-t', 'image1.jpg', '-o', '.', '--headless']
    print(args)
#     args=list(args)
    # 执行 run.py,并传递命令行参数
    process = subprocess.Popen(['python', 'run.py'] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # 获取输出
    stdout, stderr = process.communicate()
    print(stdout.decode())
    # 检查是否有错误输出
    if stderr:
        print(f'Error: {stderr.decode()}')
        return

    # 获取返回的字符串
    predictions = stdout.decode().strip()

    # 将输出格式化为指定的格式
    result = {'results': predictions}

    # 返回结果
    print(json.dumps(result))

if __name__ == '__main__':
    main()