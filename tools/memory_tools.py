
from memory.memory_store import (
    save_memory,
    search_memories,
    update_memory,
    list_memories,
    delete_memory,
    restore_memory,
    list_deleted_memories
)


def memory_save(
    content: str,
    memory_type: str,
    importance: int = 3,
    source: str = "user"
):
    """保存一条长期记忆。"""

    memory_id = save_memory(
        content=content,
        memory_type=memory_type,
        importance=importance,
        source=source
    )

    return {
        "success": True,
        "memory_id": memory_id,
        "message": "长期记忆保存成功"
    }


def memory_search(
    keyword: str = "",
    memory_type: str = None,
    limit: int = 10
):
    """搜索长期记忆。"""

    return search_memories(
        keyword=keyword,
        memory_type=memory_type,
        limit=limit
    )


def memory_update(
    memory_id: int,
    content: str = None,
    memory_type: str = None,
    importance: int = None
):
    """更新长期记忆。"""

    updated = update_memory(
        memory_id=memory_id,
        content=content,
        memory_type=memory_type,
        importance=importance
    )

    return {
        "success": updated,
        "message": "记忆更新成功" if updated else "记忆不存在或已经停用"
    }


def memory_list(
    memory_type: str = None,
    limit: int = 50
):
    """查看有效长期记忆。"""

    return list_memories(
        memory_type=memory_type,
        limit=limit
    )


def memory_delete(memory_id: int):
    """软删除长期记忆。"""

    deleted = delete_memory(memory_id)

    return {
        "success": deleted,
        "message": "记忆已停用" if deleted else "记忆不存在或已经停用"
    }


def memory_restore(memory_id: int):
    """恢复已经停用的长期记忆。"""

    restored = restore_memory(memory_id)

    return {
        "success": restored,
        "message": "记忆恢复成功" if restored else "记忆不存在或已经启用"
    }


def memory_list_deleted(limit: int = 50):
    """查看已经停用的长期记忆。"""

    return list_deleted_memories(limit=limit)
