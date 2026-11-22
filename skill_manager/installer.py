import urllib.parse
import json
import re
import shutil
import urllib.request
import urllib.error
import zipfile
import io
import truststore
import os
from dotenv import load_dotenv 

truststore.inject_into_ssl()
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
SKILLS_DIR = ROOT / "skills" / "installed"

MAX_ARCHIVE_SIZE = 20 * 1024 * 1024
MAX_SKILL_SIZE = 5 * 1024 * 1024


def request_bytes(url):
    headers = {
        "User-Agent": "MyAgent-Skill-Installer",
        "Accept": "application/vnd.github+json"
    }

    # 读取 GitHub Token
    github_token = os.getenv("GITHUB_TOKEN", "").strip()

    # 只向 GitHub API 域名发送 Token
    if github_token and urllib.parse.urlparse(url).hostname == "api.github.com":
        headers["Authorization"] = f"Bearer {github_token}"

    request = urllib.request.Request(
        url,
        headers=headers
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(MAX_ARCHIVE_SIZE + 1)

    if len(data) > MAX_ARCHIVE_SIZE:
        raise ValueError("仓库压缩包太大，超过20MB限制")

    return data


def parse_github_url(url):
    match = re.fullmatch(
        r"https://github\.com/([^/]+)/([^/]+)/?",
        url.strip().rstrip("/")
    )

    if not match:
        raise ValueError(
            "请输入完整的仓库地址，例如："
            "https://github.com/owner/repo"
        )

    owner, repo = match.groups()
    repo = repo.removesuffix(".git")

    return owner, repo


def get_repository_archive(url):
    owner, repo = parse_github_url(url)

    # 获取仓库默认分支
    api_url = f"https://api.github.com/repos/{owner}/{repo}"

    metadata = json.loads(request_bytes(api_url))
    branch = metadata.get("default_branch")

    if not branch:
        raise ValueError("无法获取仓库默认分支")

    # 下载仓库 ZIP
    zip_url = (
        f"https://api.github.com/repos/"
        f"{owner}/{repo}/zipball/{branch}"
    )

    return request_bytes(zip_url)


def read_skill_name(content):
    text = content.decode("utf-8-sig")

    parts = text.split("---", 2)

    if len(parts) < 3 or parts[0].strip():
        return None

    for line in parts[1].splitlines():
        if line.strip().startswith("name:"):
            name = line.split(":", 1)[1].strip()
            name = name.strip("'\"")

            if re.fullmatch(r"[a-z0-9-]{1,64}", name):
                return name

    return None


def discover_skills(archive_data):
    found = []

    with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:

        for info in archive.infolist():

            if info.is_dir():
                continue

            path = PurePosixPath(info.filename)

            if path.name != "SKILL.md":
                continue

            # 必须有技能文件夹
            if len(path.parts) < 2:
                continue

            # 跳过不安全路径
            if ".." in path.parts:
                continue

            # 不接受符号链接
            mode = info.external_attr >> 16

            if (mode & 0o170000) == 0o120000:
                continue

            if info.file_size > MAX_SKILL_SIZE:
                continue

            content = archive.read(info)
            name = read_skill_name(content)

            if not name:
                continue

            if name != path.parent.name:
                continue

            found.append({
                "name": name,
                "folder": str(path.parent),
                "description": "从 GitHub 仓库发现的技能"
            })

    return found


def list_github_skills(url):
    print("\n正在连接 GitHub...")

    data = get_repository_archive(url)
    skills = discover_skills(data)

    if not skills:
        print("没有发现符合格式的 SKILL.md")
        return

    print("\n========== 发现以下技能 ==========")

    for skill in skills:
        print(f"\n名称：{skill['name']}")
        print(f"目录：{skill['folder']}")

    print("\n==================================")


def install_github_skill(url, skill_name):
    print("\n正在下载 GitHub 仓库...")

    data = get_repository_archive(url)
    skills = discover_skills(data)

    selected = next(
        (s for s in skills if s["name"] == skill_name),
        None
    )

    if not selected:
        print("没有找到指定技能。")
        return

    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    target = SKILLS_DIR / skill_name

    if target.exists():
        print("该技能已经存在，暂不覆盖。")
        return

    with zipfile.ZipFile(io.BytesIO(data)) as archive:

        prefix = selected["folder"].rstrip("/") + "/"

        files = []

        for info in archive.infolist():

            path = PurePosixPath(info.filename)

            if not str(path).startswith(prefix):
                continue

            relative = path.relative_to(
                PurePosixPath(selected["folder"])
            )

            if not relative.parts:
                continue

            if ".." in relative.parts:
                raise ValueError("发现不安全的文件路径")

            mode = info.external_attr >> 16

            if (mode & 0o170000) == 0o120000:
                raise ValueError("技能包含符号链接，拒绝安装")

            if info.file_size > MAX_SKILL_SIZE:
                raise ValueError("技能文件过大，拒绝安装")

            files.append((info, relative))

        total_size = sum(info.file_size for info, _ in files)

        if total_size > MAX_SKILL_SIZE:
            raise ValueError("技能总大小超过5MB限制")

        if not files:
            print("技能目录为空。")
            return

        # 先写入临时目录，全部成功后再安装
        temp = SKILLS_DIR / f".{skill_name}.installing"

        if temp.exists():
            shutil.rmtree(temp)

        try:
            for info, relative in files:
                destination = temp.joinpath(*relative.parts)

                if not destination.resolve().is_relative_to(
                    temp.resolve()
                ):
                    raise ValueError("检测到不安全的文件路径")

                if info.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue

                destination.parent.mkdir(
                    parents=True, exist_ok=True
                )

                destination.write_bytes(archive.read(info))

            if not (temp / "SKILL.md").is_file():
                raise ValueError("技能缺少 SKILL.md")

            temp.rename(target)

        except Exception:
            if temp.exists():
                shutil.rmtree(temp)
            raise

    print(f"\n技能安装成功：{skill_name}")
    print(f"安装位置：{target}")
    print("注意：技能脚本不会自动执行。")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="MyAgent GitHub 技能安装器"
    )

    subparsers = parser.add_subparsers(
        dest="action",
        required=True
    )

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("url")

    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("url")
    install_parser.add_argument("name")

    args = parser.parse_args()

    try:
        if args.action == "list":
            list_github_skills(args.url)

        elif args.action == "install":
            install_github_skill(args.url, args.name)

    except urllib.error.HTTPError as e:
        print(f"GitHub 请求失败：HTTP {e.code}")

    except Exception as e:
        print(f"操作失败：{e}")
