
import json
import re
from pathlib import Path

# 项目路径
ROOT = Path(__file__).resolve().parent.parent

SKILLS_DIR = ROOT / "skills" / "installed"
REGISTRY_FILE = ROOT / "skills" / "registry.json"


def read_registry():
    if not REGISTRY_FILE.exists():
        return {}

    return json.loads(
        REGISTRY_FILE.read_text(encoding="utf-8")
    )


def save_registry(data):
    REGISTRY_FILE.parent.mkdir(
        parents=True, exist_ok=True
    )

    REGISTRY_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def read_skill(skill_dir):
    skill_file = skill_dir / "SKILL.md"

    if not skill_file.is_file():
        return None

    content = skill_file.read_text(encoding="utf-8")

    parts = content.split("---", 2)

    if len(parts) < 3 or parts[0].strip():
        return None

    metadata = {}

    for line in parts[1].splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")

    name = metadata.get("name", "")
    description = metadata.get("description", "")

    if not re.fullmatch(r"[a-z0-9-]{1,64}", name):
        return None

    if name != skill_dir.name:
        return None

    if not description:
        return None

    return {
        "name": name,
        "description": description,
        "instructions": parts[2].strip()
    }


def list_skills():
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    registry = read_registry()
    skills = []

    for folder in sorted(SKILLS_DIR.iterdir()):
        if not folder.is_dir():
            continue

        skill = read_skill(folder)

        if skill is None:
            continue

        name = skill["name"]

        skill["enabled"] = registry.get(
            name, True
        )

        skills.append(skill)

    return skills


def show_skills():
    skills = list_skills()

    print("\n========== MyAgent 技能管理中心 ==========")

    if not skills:
        print("暂时没有安装技能。")
        return

    for skill in skills:
        status = "已启用" if skill["enabled"] else "已停用"

        print(f"\n技能名称：{skill['name']}")
        print(f"技能说明：{skill['description']}")
        print(f"当前状态：{status}")

    print("\n==========================================")


def set_skill_status(name, enabled):
    skills = list_skills()

    if not any(s["name"] == name for s in skills):
        print("没有找到这个技能。")
        return

    registry = read_registry()
    registry[name] = enabled
    save_registry(registry)

    print(
        f"技能 {name} 已{'启用' if enabled else '停用'}。"
    )


def show_skill_details(name):
    for skill in list_skills():
        if skill["name"] == name:
            print(f"\n技能：{skill['name']}")
            print(f"说明：{skill['description']}")
            print("\n技能完整说明：")
            print(skill["instructions"])
            return

    print("没有找到这个技能。")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MyAgent 技能管理中心"
    )

    parser.add_argument(
        "action",
        choices=["list", "enable", "disable", "show"]
    )

    parser.add_argument(
        "name",
        nargs="?"
    )

    args = parser.parse_args()

    if args.action == "list":
        show_skills()

    elif args.action == "show":
        if not args.name:
            parser.error("show 命令需要技能名称")

        show_skill_details(args.name)

    elif args.action == "enable":
        if not args.name:
            parser.error("enable 命令需要技能名称")

        set_skill_status(args.name, True)

    elif args.action == "disable":
        if not args.name:
            parser.error("disable 命令需要技能名称")

        set_skill_status(args.name, False)
