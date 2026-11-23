
import os
import shutil
import tempfile
import time
from pathlib import Path


# 项目根目录
ROOT = Path(__file__).resolve().parent.parent

# 文件大小限制：2MB
MAX_FILE_SIZE = 2 * 1024 * 1024

# 允许操作的文件类型
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".json",
    ".csv", ".html", ".css", ".yaml", ".yml"
}

# 禁止操作的敏感文件和目录
BLOCKED_NAMES = {
    ".env",
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    "memory.db",
    "task_state.db"
}


def write_file(
    file_path: str,
    content: str,
    overwrite: bool = False
) -> dict:
    """
    安全地创建或写入项目目录内的文本文件。

    已有文件默认禁止覆盖。
    覆盖已有文件时，先创建备份。
    使用原子替换，降低文件损坏风险。
    """

    temp_path = None
    backup_path = None

    try:
        if not isinstance(file_path, str) or not file_path.strip():
            return {
                "success": False,
                "error": "文件路径不能为空"
            }

        if not isinstance(content, str):
            return {
                "success": False,
                "error": "文件内容必须是字符串"
            }

        # 检查内容大小
        content_size = len(content.encode("utf-8"))

        if content_size > MAX_FILE_SIZE:
            return {
                "success": False,
                "error": "写入内容超过2MB限制"
            }

        path = Path(file_path)

        # 相对路径以项目根目录为基准
        if not path.is_absolute():
            path = ROOT / path

        # 解析路径并限制在项目目录内
        path = path.resolve()
        path.relative_to(ROOT.resolve())

        # 检查敏感文件和目录
        for part in path.relative_to(ROOT.resolve()).parts:
            name = part.lower()

            if (
                name in BLOCKED_NAMES
                or name == ".env"
                or name.startswith(".env.")
            ):
                return {
                    "success": False,
                    "error": "禁止操作敏感文件或目录"
                }

        # 检查文件类型
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": "不支持写入这种文件格式"
            }

        # 检查父目录
        if not path.parent.exists():
            return {
                "success": False,
                "error": "目标目录不存在"
            }

        if not path.parent.is_dir():
            return {
                "success": False,
                "error": "目标父路径不是目录"
            }

        # 禁止覆盖目录
        if path.exists() and not path.is_file():
            return {
                "success": False,
                "error": "目标路径不是普通文件"
            }

        # 已有文件默认禁止覆盖
        if path.exists() and not overwrite:
            return {
                "success": False,
                "error": "文件已经存在，需要明确允许覆盖"
            }

        # 覆盖已有文件前创建唯一备份
        if path.exists():
            backup_path = path.with_name(
                f"{path.name}.bak-{time.time_ns()}"
            )

            shutil.copy2(path, backup_path)

        # 在目标目录创建临时文件
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            delete=False
        ) as temp_file:

            temp_path = Path(temp_file.name)

            temp_file.write(content)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        # 原子替换目标文件
        os.replace(temp_path, path)
        temp_path = None

        return {
            "success": True,
            "message": "文件写入成功",
            "file_path": str(path.relative_to(ROOT.resolve())),
            "backup_path": (
                str(backup_path.relative_to(ROOT.resolve()))
                if backup_path else None
            )
        }

    except ValueError:
        return {
            "success": False,
            "error": "禁止操作项目目录以外的文件"
        }

    except UnicodeEncodeError:
        return {
            "success": False,
            "error": "文件内容编码失败"
        }

    except Exception:
        return {
            "success": False,
            "error": "文件写入失败，请检查路径和文件权限"
        }

    finally:
        # 清理未完成的临时文件
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
