from .file_reader import read_file
from .file_writer import write_file
from .web_search import web_search

TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "web_search": web_search
}

__all__ = [
    "read_file",
    "write_file",
    "web_search",
    "TOOLS"
]