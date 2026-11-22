
from tools import TOOLS
from permissions import permission_manager


def execute_tool(tool_name: str, arguments: dict) -> dict:
    """
    统一工具执行入口：
    1. 检查工具是否存在
    2. 检查工具权限
    3. 必要时请求用户确认
    4. 执行工具
    """

    # 1. 检查工具是否存在
    tool = TOOLS.get(tool_name)

    if tool is None:
        return {
            "success": False,
            "status": "not_found",
            "error": f"不存在这个工具：{tool_name}"
        }

    # 2. 权限检查
    permission_result = permission_manager.authorize(
        tool_name,
        arguments.copy()
    )

    status = permission_result["status"]

    # 3. 如果禁止，直接拒绝
    if status == "denied":
        return {
            "success": False,
            "status": "denied",
            "error": permission_result["message"]
        }

    # 4. 如果需要确认，等待用户明确同意
    if status == "confirmation_required":

        print("\n========== 权限确认 ==========")
        print(f"MyAgent 请求执行工具：{tool_name}")
        print(f"参数：{arguments}")
        print("该操作需要你的授权。")

        confirm = input("是否允许执行？(y/n)：").strip().lower()

        if confirm != "y":
            return {
                "success": False,
                "status": "cancelled",
                "error": "用户拒绝或取消了本次操作"
            }

    # 5. 获取经过权限检查的参数
    safe_arguments = permission_result.get(
        "arguments",
        arguments
    )

    
    # 6. 执行工具
    try:
        result = tool(**safe_arguments)

        # 检查工具自身是否执行成功
        if isinstance(result, dict) and result.get("success") is False:
            return {
                "success": False,
                "status": "failed",
                "error": result.get("error", "工具执行失败"),
                "result": result
            }

        return {
            "success": True,
            "status": "completed",
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "status": "failed",
            "error": str(e)
        }
