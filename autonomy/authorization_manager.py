
import threading
import uuid
from datetime import datetime


# 保存等待授权的请求
_pending_requests = {}

# 线程安全锁
_authorization_lock = threading.Lock()


def create_authorization_request(
    task_id,
    step,
    tool_name,
    arguments
):
    """创建一个等待用户授权的请求。"""

    request_id = str(uuid.uuid4())
    event = threading.Event()

    request = {
        "request_id": request_id,
        "task_id": task_id,
        "step": step,
        "tool_name": tool_name,
        "arguments": dict(arguments),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "event": event
    }

    with _authorization_lock:
        _pending_requests[request_id] = request

    return request_id, event


def get_pending_authorizations(task_id=None):
    """获取等待授权的请求，不向网页暴露线程事件对象。"""

    with _authorization_lock:
        requests = []

        for request in _pending_requests.values():
            if request["status"] != "pending":
                continue

            if task_id and request["task_id"] != task_id:
                continue

            requests.append({
                "request_id": request["request_id"],
                "task_id": request["task_id"],
                "step": request["step"],
                "tool_name": request["tool_name"],
                "arguments": request["arguments"],
                "status": request["status"],
                "created_at": request["created_at"]
            })

        return requests


def resolve_authorization(request_id, approved):
    """处理用户的授权决定。"""

    with _authorization_lock:
        request = _pending_requests.get(request_id)

        if request is None:
            return False, "授权请求不存在或已过期"

        if request["status"] != "pending":
            return False, "该授权请求已经处理"

        request["status"] = (
            "approved" if approved else "rejected"
        )

        request["event"].set()

        return True, "授权决定已提交"


def wait_for_authorization(request_id, timeout=600):
    """等待用户授权，最多等待指定秒数。"""

    with _authorization_lock:
        request = _pending_requests.get(request_id)

    if request is None:
        return False

    event = request["event"]

    if not event.wait(timeout=timeout):
        with _authorization_lock:
            if request["status"] == "pending":
                request["status"] = "expired"
        return False

    with _authorization_lock:
        return request["status"] == "approved"
