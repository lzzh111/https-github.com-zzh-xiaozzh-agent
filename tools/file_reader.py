
from pathlib import Path

# 允许读取的项目目录
ROOT = Path(__file__).resolve().parent.parent


def read_file(file_path: str) -> dict:
    """
    读取项目目录内的文本文件。
    """

    try:
        path = Path(file_path)

        # 相对路径以项目根目录为基准
        if not path.is_absolute():
            path = ROOT / path

        # 转换为绝对路径并检查是否越界
        path = path.resolve()
        path.relative_to(ROOT.resolve())

        if not path.exists():
            return {
                "success": False,
                "error": "文件不存在"
            }

        if not path.is_file():
            return {
                "success": False,
                "error": "指定路径不是文件"
            }

        # 限制文件大小为 2MB
        if path.stat().st_size > 2 * 1024 * 1024:
            return {
                "success": False,
                "error": "文件太大，暂时只支持 2MB 以内的文件"
            }

        # 暂时只支持文本文件
        allowed_extensions = {
            ".txt", ".md", ".py", ".js", ".json",
            ".csv", ".html", ".css", ".yaml", ".yml"
        }

        if path.suffix.lower() not in allowed_extensions:
            return {
                "success": False,
                "error": "暂不支持读取这种文件格式"
            }

        content = path.read_text(encoding="utf-8")

        return {
            "success": True,
            "file_name": path.name,
            "content": content
        }

    except ValueError:
        return {
            "success": False,
            "error": "不能读取项目目录以外的文件"
        }

    except UnicodeDecodeError:
        return {
            "success": False,
            "error": "文件不是有效的 UTF-8 文本"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
