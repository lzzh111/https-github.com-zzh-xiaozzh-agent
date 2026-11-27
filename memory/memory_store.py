
import sqlite3
from pathlib import Path
from datetime import datetime


# 长期记忆数据库路径
ROOT = Path(__file__).resolve().parent.parent
MEMORY_DB_PATH = ROOT / "long_term_memory.db"


def get_connection():
    """创建长期记忆数据库连接。"""
    return sqlite3.connect(MEMORY_DB_PATH)


def init_memory_db():
    """初始化长期记忆数据库。"""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                importance INTEGER DEFAULT 3,
                source TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_memories_type
            ON memories(memory_type)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
            idx_memories_active
            ON memories(is_active)
        """)

def save_memory(
    content: str,
    memory_type: str,
    importance: int = 3,
    source: str = "user"
):
    """
    保存一条长期记忆。

    memory_type:
        user_fact  用户事实
        preference 用户偏好
        project    项目信息
        experience 经验信息
    """

    allowed_types = {
        "user_fact",
        "preference",
        "project",
        "experience"
    }

    if not isinstance(content, str) or not content.strip():
        raise ValueError("记忆内容不能为空")

    if memory_type not in allowed_types:
        raise ValueError("不支持的记忆类型")

    if not isinstance(importance, int) or isinstance(importance, bool) or not 1 <= importance <= 5:
        raise ValueError("重要程度必须是 1 到 5")

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO memories (
                content,
                memory_type,
                importance,
                source,
                is_active,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, 1, ?, ?)
        """, (
            content.strip(),
            memory_type,
            importance,
            source,
            now,
            now
        ))

        return cursor.lastrowid

def search_memories(
    keyword: str = "",
    memory_type: str = None,
    limit: int = 10
):
    """
    根据关键词和记忆类型检索有效记忆。
    """

    if not isinstance(keyword, str):
        raise ValueError("关键词必须是字符串")

    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit 必须是正整数")

    allowed_types = {
        "user_fact",
        "preference",
        "project",
        "experience"
    }

    if memory_type is not None and memory_type not in allowed_types:
        raise ValueError("不支持的记忆类型")

    sql = """
        SELECT
            id,
            content,
            memory_type,
            importance,
            source,
            created_at,
            updated_at
        FROM memories
        WHERE is_active = 1
    """

    params = []

    if keyword.strip():
        sql += " AND content LIKE ?"
        params.append(f"%{keyword.strip()}%")

    if memory_type:
        sql += " AND memory_type = ?"
        params.append(memory_type)

    sql += """
        ORDER BY importance DESC, updated_at DESC
        LIMIT ?
    """

    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    columns = [
        "id",
        "content",
        "memory_type",
        "importance",
        "source",
        "created_at",
        "updated_at"
    ]

    return [
        dict(zip(columns, row))
        for row in rows
    ]

def update_memory(
    memory_id: int,
    content: str = None,
    memory_type: str = None,
    importance: int = None
):
    """根据记忆 ID 更新记忆内容或属性。"""

    if not isinstance(memory_id, int) or isinstance(memory_id, bool) or memory_id < 1:
        raise ValueError("记忆 ID 必须是正整数")

    allowed_types = {
        "user_fact",
        "preference",
        "project",
        "experience"
    }

    updates = []
    params = []

    if content is not None:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("记忆内容不能为空")
        updates.append("content = ?")
        params.append(content.strip())

    if memory_type is not None:
        if memory_type not in allowed_types:
            raise ValueError("不支持的记忆类型")
        updates.append("memory_type = ?")
        params.append(memory_type)

    if importance is not None:
        if (
            not isinstance(importance, int)
            or isinstance(importance, bool)
            or not 1 <= importance <= 5
        ):
            raise ValueError("重要程度必须是 1 到 5")
        updates.append("importance = ?")
        params.append(importance)

    if not updates:
        raise ValueError("至少提供一个需要更新的字段")

    updates.append("updated_at = ?")
    params.append(datetime.now().isoformat(timespec="seconds"))
    params.append(memory_id)

    with get_connection() as conn:
        cursor = conn.execute(
            f"""
                UPDATE memories
                SET {", ".join(updates)}
                WHERE id = ? AND is_active = 1
            """,
            params
        )

        return cursor.rowcount > 0

def delete_memory(memory_id: int):
    """停用一条长期记忆，不直接删除数据库记录。"""

    if (
        not isinstance(memory_id, int)
        or isinstance(memory_id, bool)
        or memory_id < 1
    ):
        raise ValueError("记忆 ID 必须是正整数")

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE memories
            SET is_active = 0,
                updated_at = ?
            WHERE id = ? AND is_active = 1
        """, (now, memory_id))

        return cursor.rowcount > 0

def list_memories(
    memory_type: str = None,
    limit: int = 50
):
    """列出有效记忆，支持按类型筛选。"""

    allowed_types = {
        "user_fact",
        "preference",
        "project",
        "experience"
    }

    if memory_type is not None and memory_type not in allowed_types:
        raise ValueError("不支持的记忆类型")

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        raise ValueError("limit 必须是正整数")

    sql = """
        SELECT
            id,
            content,
            memory_type,
            importance,
            source,
            created_at,
            updated_at
        FROM memories
        WHERE is_active = 1
    """

    params = []

    if memory_type:
        sql += " AND memory_type = ?"
        params.append(memory_type)

    sql += """
        ORDER BY importance DESC, updated_at DESC
        LIMIT ?
    """

    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    columns = [
        "id",
        "content",
        "memory_type",
        "importance",
        "source",
        "created_at",
        "updated_at"
    ]

    return [dict(zip(columns, row)) for row in rows]

def restore_memory(memory_id: int):
    """恢复一条已经停用的长期记忆。"""

    if (
        not isinstance(memory_id, int)
        or isinstance(memory_id, bool)
        or memory_id < 1
    ):
        raise ValueError("记忆 ID 必须是正整数")

    now = datetime.now().isoformat(timespec="seconds")

    with get_connection() as conn:
        cursor = conn.execute("""
            UPDATE memories
            SET is_active = 1,
                updated_at = ?
            WHERE id = ? AND is_active = 0
        """, (now, memory_id))

        return cursor.rowcount > 0

def list_deleted_memories(limit: int = 50):
    """列出所有已经停用的长期记忆。"""

    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or limit < 1
    ):
        raise ValueError("limit 必须是正整数")

    with get_connection() as conn:
        rows = conn.execute("""
            SELECT
                id,
                content,
                memory_type,
                importance,
                source,
                created_at,
                updated_at
            FROM memories
            WHERE is_active = 0
            ORDER BY updated_at DESC
            LIMIT ?
        """, (limit,)).fetchall()

    columns = [
        "id",
        "content",
        "memory_type",
        "importance",
        "source",
        "created_at",
        "updated_at"
    ]

    return [dict(zip(columns, row)) for row in rows]

