
from pathlib import Path

# 允许读取的项目目录
ROOT = Path(__file__).resolve().parent.parent

# 允许读取的文件类型
ALLOWED_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".json",
    ".csv", ".html", ".css", ".yaml", ".yml"
}

# 文件大小限制：2MB
MAX_SIZE = 2 * 1024 * 1024


def read_file(
    file_path: str,
    start_line: int = None,
    end_line: int = None
) -> dict:
    """
    读取项目目录内的文本文件。

    可以读取整个文件，也可以指定行数范围。
    行号从 1 开始。
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
        if path.stat().st_size > MAX_SIZE:
            return {
                "success": False,
                "error": "文件太大，暂时只支持 2MB 以内的文件"
            }

        # 检查文件格式
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": "暂不支持读取这种文件格式"
            }

        # 检查行号参数
        if start_line is not None:
            if not isinstance(start_line, int) or isinstance(start_line, bool) or start_line < 1:
                return {
                    "success": False,
                    "error": "start_line 必须是大于等于 1 的整数"
                }

        if end_line is not None:
            if not isinstance(end_line, int) or isinstance(end_line, bool) or end_line < 1:
                return {
                    "success": False,
                    "error": "end_line 必须是大于等于 1 的整数"
                }

        if start_line is not None and end_line is not None:
            if start_line > end_line:
                return {
                    "success": False,
                    "error": "start_line 不能大于 end_line"
                }

        # 读取文件内容
        content = path.read_text(encoding="utf-8")
        lines = content.splitlines()

        total_lines = len(lines)

        # 按行截取
        first = start_line if start_line is not None else 1
        last = end_line if end_line is not None else total_lines

        selected_lines = lines[first - 1:last]

        return {
            "success": True,
            "file_name": path.name,
            "start_line": first,
            "end_line": min(last, total_lines),
            "total_lines": total_lines,
            "content": "\n".join(selected_lines)
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
