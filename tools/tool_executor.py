
from tools import TOOLS
from permissions import permission_manager

from autonomy.authorization_manager import (
    create_authorization_request,
    wait_for_authorization
)


def notify_progress(callback, event):
    """安全地发送授权进度事件。"""
    if callback:
        try:
            callback(event)
        except Exception as e:
            print("[小zzh] 授权进度通知失败：", e)


def execute_tool(
    tool_name: str,
    arguments: dict,
    task_id=None,
    step=None,
    progress_callback=None
) -> dict:
    """
    统一工具执行入口：
    1. 检查工具是否存在
    2. 检查工具权限
    3. 必要时等待网页授权
    4. 执行工具
    5. 准确返回执行结果
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

    # 3. 禁止执行
    if status == "denied":
        return {
            "success": False,
            "status": "denied",
            "error": permission_result["message"]
        }

    # 4. 获取经过权限检查的参数
    safe_arguments = permission_result.get(
        "arguments",
        arguments
    )

    # 5. 需要用户授权
    if status == "confirmation_required":

        # 没有任务上下文时，不允许执行需要授权的操作
        if not task_id or step is None:
            return {
                "success": False,
                "status": "confirmation_required",
                "error": "该操作需要通过自主任务模式完成网页授权"
            }

        request_id, authorization_event = (
            create_authorization_request(
                task_id=task_id,
                step=step,
                tool_name=tool_name,
                arguments=safe_arguments
            )
        )

        # 通知网页展示授权请求
        notify_progress(progress_callback, {
            "type": "authorization_required",
            "request_id": request_id,
            "task_id": task_id,
            "step": step,
            "tool_name": tool_name,
            "arguments": safe_arguments,
            "status": "pending",
            "message": "小zzh 请求执行一项需要授权的操作"
        })

        # 等待用户决定
        approved = wait_for_authorization(request_id)

        if not approved:
            return {
                "success": False,
                "status": "cancelled",
                "error": "用户拒绝授权或授权等待超时"
            }

    # 6. 执行工具
    try:
        result = tool(**safe_arguments)

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
