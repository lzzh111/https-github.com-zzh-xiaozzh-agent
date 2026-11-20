
from tools import read_file

result = read_file("test.txt")

if result["success"]:
    print("读取成功！")
    print("文件名称：", result["file_name"])
    print("文件内容：")
    print(result["content"])
else:
    print("读取失败：", result["error"])
