
from pathlib import Path
import shutil

# 项目根目录
ROOT = Path(__file__).resolve().parent.parent

# 允许写入的文本文件格式
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".json",
    ".csv", ".html", ".css", ".yaml", ".yml"
}

# 禁止修改的目录和文件
BLOCKED_NAMES = {
    ".env",
    ".git",
    ".venv",
    "__pycache__",
    "memory.db",
    "task_state.db"
}

# 最大写入内容：2MB
MAX_SIZE = 2 * 1024 * 1024


def write_file(file_path: str, content: str) -> dict:
    """
    安全地写入项目目录内的文本文件。
    如果原文件存在，写入前自动备份。
    """

    try:
        path = Path(file_path)

        # 相对路径以项目根目录为基准
        if not path.is_absolute():
            path = ROOT / path

        # 转换为绝对路径
        path = path.resolve()

        # 禁止访问项目目录之外的文件
        path.relative_to(ROOT.resolve())

        # 检查敏感文件和目录
        relative_parts = path.relative_to(ROOT.resolve()).parts

        if any(part in BLOCKED_NAMES for part in relative_parts):
            return {
                "success": False,
                "error": "禁止修改敏感文件或目录"
            }

        # 检查文件格式
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": "暂不支持修改这种文件格式"
            }

        # 检查写入内容
        if not isinstance(content, str):
            return {
                "success": False,
                "error": "写入内容必须是文本"
            }

        content_size = len(content.encode("utf-8"))

        if content_size > MAX_SIZE:
            return {
                "success": False,
                "error": "写入内容超过2MB限制"
            }

        # 创建父目录
        path.parent.mkdir(parents=True, exist_ok=True)

        # 如果原文件存在，先备份
        backup_path = None

        if path.exists():
            if not path.is_file():
                return {
                    "success": False,
                    "error": "指定路径不是文件"
                }

            backup_path = path.with_name(path.name + ".bak")
            shutil.copy2(path, backup_path)

        try:
            # 写入文件
            path.write_text(content, encoding="utf-8")

        except Exception:
            # 写入失败时恢复原文件
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, path)

            raise

        return {
            "success": True,
            "file_name": path.name,
            "file_path": str(path),
            "backup_path": str(backup_path) if backup_path else None,
            "message": "文件写入成功"
        }

    except ValueError:
        return {
            "success": False,
            "error": "不能修改项目目录以外的文件"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
