
from .file_reader import read_file
from .file_writer import write_file
from .web_search import web_search
from .memory_tools import (
    memory_save,
    memory_search,
    memory_update,
    memory_list,
    memory_delete,
    memory_restore,
    memory_list_deleted
)

TOOLS = {
    "read_file": read_file,
    "write_file": write_file,
    "web_search": web_search,

    "memory_save": memory_save,
    "memory_search": memory_search,
    "memory_update": memory_update,
    "memory_list": memory_list,
    "memory_delete": memory_delete,
    "memory_restore": memory_restore,
    "memory_list_deleted": memory_list_deleted
}
__all__ = [
    "read_file",
    "write_file",
    "web_search",
    "TOOLS"
]
