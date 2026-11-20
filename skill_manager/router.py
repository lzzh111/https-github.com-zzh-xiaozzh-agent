
from .loader import list_available_skills, load_skill





SKILL_KEYWORDS = {
    "code-review": [
        "代码审查",
        "代码检查",
        "代码评审",
        "检查代码",
        "审查代码",
        "审查一下代码",
        "帮我审查",
        "检查一下代码",
        "帮我检查一下我的代码有没有问题",
        "代码质量",
        "代码规范",
        "review",
        "code review",
        "pr review",
        "pull request",
        "分支审查",
        "审查分支",
    ]
}



def match_skill(user_request):
    """根据用户需求匹配最合适的技能。"""

    request = user_request.lower().strip()

    if not request:
        return None

    available_skills = list_available_skills()

    best_skill = None
    best_score = 0

    for skill in available_skills:
        name = skill["name"]
        keywords = SKILL_KEYWORDS.get(name, [])

        score = 0

        # 技能名称匹配
        if name.lower() in request:
            score += 5

        # 技能关键词匹配
        for keyword in keywords:
            if keyword.lower() in request:
                score += 3

        # 技能说明匹配
        description = skill["description"].lower()

        if "review" in request and "review" in description:
            score += 2

        if score > best_score:
            best_score = score
            best_skill = name

    if best_skill:
        return load_skill(best_skill)

    return None


if __name__ == "__main__":
    print("MyAgent 技能匹配测试")
    print("-" * 40)

    request = input("请输入你的需求：")

    skill = match_skill(request)

    if skill:
        print("\n成功匹配技能！")
        print("技能名称：", skill["name"])
        print("技能说明：", skill["description"])
        print("\n技能指令已加载。")
    else:
        print("\n暂时没有找到合适的技能。")
