
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / "skills" / "installed"
REGISTRY_FILE = ROOT / "skills" / "registry.json"


def read_registry():
    """读取技能启用状态。"""
    if not REGISTRY_FILE.exists():
        return {}

    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def parse_skill(skill_file):
    """读取并解析一个 SKILL.md 文件。"""
    content = skill_file.read_text(encoding="utf-8")

    match = re.match(
        r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z",
        content,
        re.DOTALL
    )

    if not match:
        raise ValueError("SKILL.md 缺少有效的 YAML frontmatter")

    metadata_text = match.group(1)
    instructions = match.group(2).strip()

    metadata = {}

    for line in metadata_text.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip("'\"")

    name = metadata.get("name", "").strip()
    description = metadata.get("description", "").strip()

    if not name or not description:
        raise ValueError("技能缺少 name 或 description")

    return {
        "name": name,
        "description": description,
        "instructions": instructions,
        "path": str(skill_file.parent)
    }


def load_skill(name):
    """按名称读取一个已启用的技能。"""
    registry = read_registry()

    # 兼容 registry 中直接保存布尔值的情况
    status = registry.get(name, True)

    if isinstance(status, dict):
        enabled = status.get("enabled", True)
    else:
        enabled = status

    if not enabled:
        raise ValueError(f"技能 {name} 当前处于禁用状态")

    skill_file = SKILLS_DIR / name / "SKILL.md"

    if not skill_file.is_file():
        raise FileNotFoundError(f"找不到技能文件：{skill_file}")

    skill = parse_skill(skill_file)

    if skill["name"] != name:
        raise ValueError("技能名称与文件夹名称不一致")

    return skill


def list_available_skills():
    """列出所有已启用且可读取的技能。"""
    if not SKILLS_DIR.exists():
        return []

    registry = read_registry()
    result = []

    for skill_file in SKILLS_DIR.glob("*/SKILL.md"):
        name = skill_file.parent.name
        status = registry.get(name, True)

        if isinstance(status, dict):
            enabled = status.get("enabled", True)
        else:
            enabled = status

        if not enabled:
            continue

        try:
            result.append(parse_skill(skill_file))
        except (ValueError, OSError):
            continue

    return result


if __name__ == "__main__":
    skills = list_available_skills()

    print(f"发现 {len(skills)} 个可用技能：\n")

    for skill in skills:
        print(f"技能名称：{skill['name']}")
        print(f"技能说明：{skill['description']}")
        print("-" * 50)
