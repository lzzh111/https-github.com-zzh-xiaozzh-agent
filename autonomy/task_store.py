
import sqlite3
import json
import uuid
from pathlib import Path
from datetime import datetime


# 数据库单独存放，不与 V2 的 memory.db 混用
ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "task_state.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    """初始化任务状态数据库。"""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS task_runs (
                task_id TEXT PRIMARY KEY,
                task_name TEXT,
                plan_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def create_task(plan: dict) -> str:
    """创建任务记录，保存初始计划。"""

    task_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    with get_connection() as conn:
        conn.execute("""
            INSERT INTO task_runs
            (task_id, task_name, plan_json, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            plan.get("task", "未命名任务"),
            json.dumps(plan, ensure_ascii=False),
            "pending",
            now,
            now
        ))

    return task_id


def update_task(task_id: str, plan: dict, status: str):
    """更新任务计划和执行状态。"""

    now = datetime.now().isoformat()

    with get_connection() as conn:
        conn.execute("""
            UPDATE task_runs
            SET plan_json = ?, status = ?, updated_at = ?
            WHERE task_id = ?
        """, (
            json.dumps(plan, ensure_ascii=False),
            status,
            now,
            task_id
        ))


def get_task(task_id: str):
    """根据任务 ID 读取任务记录。"""

    with get_connection() as conn:
        row = conn.execute("""
            SELECT task_id, task_name, plan_json, status,
                   created_at, updated_at
            FROM task_runs
            WHERE task_id = ?
        """, (task_id,)).fetchone()

    if row is None:
        return None

    return {
        "task_id": row[0],
        "task_name": row[1],
        "plan": json.loads(row[2]),
        "status": row[3],
        "created_at": row[4],
        "updated_at": row[5]
    }





def get_tasks(status=None, page=1, limit=20, keyword=None):
    """获取历史任务列表，支持状态筛选、搜索和分页。"""

    if page < 1:
        raise ValueError("page 不能小于 1")

    if limit < 1 or limit > 100:
        raise ValueError("limit 必须在 1 到 100 之间")

    conditions = []
    params = []

    # 状态筛选
    if status:
        conditions.append("status = ?")
        params.append(status)

    # 关键词搜索
    if keyword:
        conditions.append("task_name LIKE ?")
        params.append(f"%{keyword}%")

    where_sql = ""

    if conditions:
        where_sql = "WHERE " + " AND ".join(conditions)

    with get_connection() as conn:

        # 查询任务总数
        count_sql = f"""
            SELECT COUNT(*)
            FROM task_runs
            {where_sql}
        """

        total = conn.execute(
            count_sql,
            params
        ).fetchone()[0]

        # 分页查询
        offset = (page - 1) * limit

        query_sql = f"""
            SELECT task_id, task_name, status,
                   created_at, updated_at
            FROM task_runs
            {where_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """

        rows = conn.execute(
            query_sql,
            params + [limit, offset]
        ).fetchall()

    tasks = []

    for row in rows:
        tasks.append({
            "task_id": row[0],
            "task_name": row[1],
            "status": row[2],
            "created_at": row[3],
            "updated_at": row[4]
        })

    total_pages = (total + limit - 1) // limit

    return {
        "tasks": tasks,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }




if __name__ == "__main__":
    init_db()

    demo_plan = {
        "task": "测试任务",
        "steps": [
            {
                "step": 1,
                "description": "测试任务持久化",
                "tool": "web_search",
                "status": "pending"
            }
        ]
    }

    task_id = create_task(demo_plan)

    print("任务保存成功！")
    print("任务 ID：", task_id)
    print("读取结果：")
    print(json.dumps(
        get_task(task_id),
        ensure_ascii=False,
        indent=4
    ))
