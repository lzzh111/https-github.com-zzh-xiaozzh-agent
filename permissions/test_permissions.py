
from tools.tool_executor import execute_tool


# 测试一：不存在的工具
print("\n测试一：不存在的工具")

result = execute_tool(
    "unknown_tool",
    {}
)

print(result)


# 测试二：禁止执行的工具
print("\n测试二：禁止执行的工具")

result = execute_tool(
    "delete_file",
    {"file_path": "test.txt"}
)

print(result)


# 测试三：需要用户确认的工具
print("\n测试三：需要用户确认的工具")

result = execute_tool(
    "send_email",
    {
        "to": "example@example.com"
    }
)

print(result)
