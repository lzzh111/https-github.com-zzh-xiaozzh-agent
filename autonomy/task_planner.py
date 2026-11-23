
import json
from skill_manager.ai_router import client, MODEL


def create_task_plan(user_request: str) -> dict:
    """
    将用户的复杂任务拆解成可执行步骤。
    这里只负责规划，不执行任务。
    """

    system_prompt = """
你是 小zzh 的任务规划器。

你的工作是把用户的复杂任务拆解成清晰、可执行的步骤。

规则：
1. 根据任务复杂程度决定步骤数量，通常为2到8步。
2. 每一步都要明确说明要完成什么。
3. 判断每一步需要什么工具。
4. 只能使用以下工具：
   - web_search：网页搜索
   - read_file：读取文件
   - write_file：创建或写入文件

5. 如果用户要求创建或写入文件，必须选择 write_file。

6. 如果使用 write_file，必须在步骤描述中明确包含：
   - file_path：用户指定的完整目标文件路径
   - content：用户要求写入的完整内容
   - overwrite：是否允许覆盖，默认 false

7. 不得擅自编造文件路径或文件内容。
8. 不要声称已经执行任务。
9. 不要生成危险、违法或未经用户授权的操作。
10. 只返回合法 JSON，不要使用 Markdown 代码块。

返回格式：
{
    "task": "任务名称",
    "steps": [
        {
            "step": 1,
            "description": "具体任务",
            "tool": "web_search",
            "status": "pending"
        }
    ]
}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_request
                }
            ],
            response_format={"type": "json_object"},
            extra_body={
                "thinking": {
                    "type": "disabled"
                }
            }
        )

        content = response.choices[0].message.content

        plan = json.loads(content)

        if not isinstance(plan.get("steps"), list):
            raise ValueError("任务计划格式不正确")

        if not 1 <= len(plan["steps"]) <= 8:
            raise ValueError("任务步骤数量必须在1到8步之间")

        for index, step in enumerate(plan["steps"], 1):
            step["step"] = index
            step["status"] = "pending"

        return {
            "success": True,
            "plan": plan
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":

    request = input("请输入一个复杂任务：")

    result = create_task_plan(request)

    print("\nMyAgent 任务规划结果：")

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=4
        )
    )
