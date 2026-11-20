
from enum import Enum
from pathlib import Path
import json


class PermissionLevel(str, Enum):
    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


class PermissionManager:

    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent
        self.config_path = Path(__file__).resolve().parent / "permissions.json"

        # 默认权限
        self.permissions = {
            "read_file": PermissionLevel.ALLOW,
            "web_search": PermissionLevel.ALLOW,
            "analyze_csv": PermissionLevel.ALLOW,

            "write_file": PermissionLevel.CONFIRM,
            "send_email": PermissionLevel.CONFIRM,
            "update_customer": PermissionLevel.CONFIRM,

            "delete_file": PermissionLevel.DENY,
            "execute_command": PermissionLevel.DENY,
            "make_payment": PermissionLevel.DENY,
        }

        self.load_permissions()

    def load_permissions(self):
        """从 JSON 文件加载权限配置。"""

        if not self.config_path.exists():
            self.save_permissions()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                raise ValueError("权限配置必须是 JSON 对象")

            for name, value in data.items():
                self.permissions[name] = PermissionLevel(value)

        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"权限配置文件格式错误：{e}")

    def save_permissions(self):
        """保存权限配置到 JSON 文件。"""

        data = {
            name: level.value
            for name, level in self.permissions.items()
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def set_permission(self, tool_name, level):
        """修改工具权限并保存。"""

        if not isinstance(level, PermissionLevel):
            level = PermissionLevel(level)

        self.permissions[tool_name] = level
        self.save_permissions()

    def get_permission(self, tool_name):
        """查询工具权限，未登记的工具默认禁止。"""

        return self.permissions.get(
            tool_name,
            PermissionLevel.DENY
        )

    def check_file_path(self, file_path):
        """限制文件只能访问项目目录内的路径。"""

        try:
            path = Path(file_path)

            if not path.is_absolute():
                path = self.project_root / path

            path = path.resolve()

            if not path.is_relative_to(self.project_root):
                return False, "禁止访问项目目录之外的文件"

            return True, str(path)

        except (OSError, ValueError) as e:
            return False, f"文件路径检查失败：{e}"

    def authorize(self, tool_name, arguments=None):
        """检查工具是否有执行权限。"""

        arguments = dict(arguments or {})
        permission = self.get_permission(tool_name)

        if permission == PermissionLevel.DENY:
            return {
                "allowed": False,
                "status": "denied",
                "message": f"工具 {tool_name} 没有执行权限"
            }

        if tool_name in ("read_file", "write_file", "delete_file"):
            file_path = arguments.get("file_path")

            if not file_path:
                return {
                    "allowed": False,
                    "status": "denied",
                    "message": "缺少文件路径"
                }

            valid, result = self.check_file_path(file_path)

            if not valid:
                return {
                    "allowed": False,
                    "status": "denied",
                    "message": result
                }

            arguments["file_path"] = result

        if permission == PermissionLevel.CONFIRM:
            return {
                "allowed": False,
                "status": "confirmation_required",
                "message": f"执行 {tool_name} 前需要用户确认",
                "arguments": arguments
            }

        return {
            "allowed": True,
            "status": "approved",
            "message": "权限检查通过",
            "arguments": arguments
        }


# 创建全局权限管理器
permission_manager = PermissionManager()


if __name__ == "__main__":

    print("MyAgent 权限管理系统测试")
    print("=" * 40)

    tests = [
        ("web_search", {"query": "AI Agent"}),
        ("read_file", {"file_path": "test.txt"}),
        ("send_email", {"to": "example@example.com"}),
        ("delete_file", {"file_path": "test.txt"}),
        ("unknown_tool", {})
    ]

    for name, arguments in tests:
        result = permission_manager.authorize(name, arguments)

        print(f"\n工具：{name}")
        print("权限状态：", result["status"])
        print("说明：", result["message"])
