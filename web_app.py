
import threading
import uuid
from autonomy.task_executor import run_task
from flask import Flask, jsonify, render_template, request

from main import init_db, load_history, save_message
from tools.ai_tools import ask_with_tools
from autonomy.task_store import (
    init_db as init_task_db,
    get_tasks,
    get_task
)


app = Flask(__name__)

request_lock = threading.Lock()

# 保存当前运行中的任务进度
task_progress = {}
progress_lock = threading.Lock()


def update_progress(task_id, event):
    """后台任务通过这个函数更新网页进度。"""
    with progress_lock:
        task_progress[task_id]["events"].append(event)
        task_progress[task_id]["latest"] = event

        if event.get("type") in (
            "task_finished",
            "task_error",
            "report_ready"
        ):
            task_progress[task_id]["finished"] = True


def run_background_task(task_id, user_request):
    """在线程中执行自主任务，不阻塞网页请求。"""

    try:
        result = run_task( 
            user_request,
            progress_callback=lambda event: update_progress(
                task_id, event
            )
        )

        with progress_lock:
            task_progress[task_id]["report"] = result
            task_progress[task_id]["finished"] = True

    except Exception as e:
        update_progress(task_id, {
            "type": "task_error",
            "status": "failed",
            "message": str(e)
        })


@app.route("/")
def index():
    return render_template("index.html")



@app.route("/api/tasks", methods=["GET"])
def get_tasks_api():
    """获取历史任务列表，支持筛选、搜索和分页。"""

    try:
        init_task_db()

        # 获取查询参数
        status = request.args.get("status", "all").strip()
        keyword = request.args.get("keyword", "").strip()

        try:
            page = int(request.args.get("page", 1))
            limit = int(request.args.get("limit", 20))
        except (TypeError, ValueError):
            return jsonify({
                "success": False,
                "error": "page 和 limit 必须是整数"
            }), 400

        # 参数范围校验
        if page < 1:
            return jsonify({
                "success": False,
                "error": "page 不能小于 1"
            }), 400

        if limit < 1 or limit > 100:
            return jsonify({
                "success": False,
                "error": "limit 必须在 1 到 100 之间"
            }), 400

        # 状态白名单
        allowed_statuses = {
            "all",
            "pending",
            "running",
            "completed",
            "failed",
            "paused"
        }

        if status not in allowed_statuses:
            return jsonify({
                "success": False,
                "error": "不支持的任务状态"
            }), 400

        if len(keyword) > 100:
            return jsonify({
                "success": False,
                "error": "搜索关键词不能超过 100 个字符"
            }), 400

        # all 表示查询全部状态
        if status == "all":
            status = None

        result = get_tasks(
            status=status,
            page=page,
            limit=limit,
            keyword=keyword or None
        )

        return jsonify({
            "success": True,
            "tasks": result["tasks"],
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
            "total_pages": result["total_pages"]
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task_detail_api(task_id):
    """获取单个历史任务的完整详情。"""

    try:
        init_task_db()

        task = get_task(task_id)

        if not task:
            return jsonify({
                "success": False,
                "error": "找不到这个任务"
            }), 404

        return jsonify({
            "success": True,
            "task": task
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

    try:
        init_db()

        return jsonify({
            "success": True,
            "history": load_history()
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_text = str(data.get("message", "")).strip()

    if not user_text:
        return jsonify({
            "success": False,
            "error": "请输入消息"
        }), 400

    try:
        with request_lock:
            init_db()
            history = load_history()

            answer = ask_with_tools(
                user_request=user_text,
                history=history
            )

            answer = str(answer)

            save_message("user", user_text)
            save_message("assistant", answer)

        return jsonify({
            "success": True,
            "answer": answer
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/task/start", methods=["POST"])
def start_task():
    data = request.get_json(silent=True) or {}
    user_request = str(data.get("message", "")).strip()

    if not user_request:
        return jsonify({
            "success": False,
            "error": "请输入任务内容"
        }), 400

    task_id = str(uuid.uuid4())

    with progress_lock:
        task_progress[task_id] = {
            "events": [],
            "latest": {
                "type": "queued",
                "status": "running",
                "message": "任务已进入执行队列"
            },
            "report": None,
            "finished": False
        }

    thread = threading.Thread(
        target=run_background_task,
        args=(task_id, user_request),
        daemon=True
    )
    thread.start()

    return jsonify({
        "success": True,
        "task_id": task_id,
        "message": "任务已启动"
    })


@app.route("/api/task/progress/<task_id>", methods=["GET"])
def get_task_progress(task_id):
    with progress_lock:
        task = task_progress.get(task_id)

        if not task:
            return jsonify({
                "success": False,
                "error": "找不到这个运行中的任务"
            }), 404

        return jsonify({
            "success": True,
            "events": list(task["events"]),
            "latest": task["latest"],
            "report": task["report"],
            "finished": task["finished"]
        })


if __name__ == "__main__":
    init_db()
    init_task_db()

    print("小zzh 网页工作空间启动中……")
    print("浏览器访问：http://127.0.0.1:5000")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )
