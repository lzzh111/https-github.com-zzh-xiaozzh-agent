
import json
import inspect

from autonomy.task_store import (
    init_db,
    create_task,
    update_task
)
from autonomy.result_checker import check_execution_result

from skill_manager.ai_router import client, MODEL
from autonomy.task_planner import create_task_plan

from tools import TOOLS
from tools.tool_executor import execute_tool

from permissions.permission_manager import permission_manager


def notify_progress(callback, event):
    """安全地向网页发送进度事件。"""
    if callback:
        try:
            callback(event)
        except Exception as e:
            print("[小zzh] 进度通知失败：", e)


def generate_tool_arguments(step, previous_results):
    """根据任务步骤，让 AI 生成工具调用参数。"""

    tool_name = step["tool"]

    if tool_name not in TOOLS:
        raise ValueError(f"不存在这个工具：{tool_name}")

    tool_function = TOOLS[tool_name]
    signature = inspect.signature(tool_function)

    parameters = {}

    for name, param in signature.parameters.items():
        if name in ("self", "kwargs"):
            continue

        parameters[name] = {
            "required": param.default == inspect.Parameter.empty
        }

    prompt = f"""
你是小zzh的工具参数生成器。

请根据任务步骤生成工具调用参数。

工具名称：
{tool_name}

工具可用参数：
{json.dumps(parameters, ensure_ascii=False)}

当前任务步骤：
{step["description"]}

之前步骤的执行结果：
{json.dumps(previous_results, ensure_ascii=False, default=str)}

要求：
1. 只返回 JSON 对象。
2. 参数名称必须来自工具可用参数。
3. 不要编造文件路径、搜索结果或其他事实。
4. 如果缺少必要信息，不要猜测，返回空对象。

返回格式：
{{}}
"""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        extra_body={"thinking": {"type": "disabled"}}
    )

    content = response.choices[0].message.content
    arguments = json.loads(content)

    if not isinstance(arguments, dict):
        raise ValueError("AI 生成的工具参数格式不正确")

    allowed_parameters = set(parameters.keys())

    if not set(arguments.keys()).issubset(allowed_parameters):
        raise ValueError("AI 生成了工具不支持的参数")

    missing = [
        name for name, info in parameters.items()
        if info["required"] and name not in arguments
    ]

    if missing:
        raise ValueError(f"缺少必要参数：{', '.join(missing)}")

    return arguments


def save_task_progress(task_id, plan, status, results=None):
    """将任务计划、执行结果和状态保存到 SQLite。"""

    if results is not None:
        plan["results"] = results

    if task_id:
        update_task(task_id, plan, status)


def execute_task_plan(plan, task_id=None, progress_callback=None):
    """逐步执行任务，并实时发送进度。"""

    if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
        return {
            "success": False,
            "status": "failed",
            "error": "任务计划格式不正确"
        }

    results = []
    MAX_RETRIES = 2

    RETRYABLE_TOOLS = {
        "web_search",
        "read_file",
        "analyze_csv"
    }

    total_steps = len(plan["steps"])

    save_task_progress(task_id, plan, "running")

    notify_progress(progress_callback, {
        "type": "task_started",
        "task": plan.get("task"),
        "total_steps": total_steps,
        "status": "running",
        "message": "任务规划完成，开始执行"
    })

    for index, step in enumerate(plan["steps"]):

        step_number = step.get("step", index + 1)
        tool_name = step.get("tool")
        description = step.get("description", "")

        print(f"\n[小zzh] 正在执行第 {step_number} 步")
        print("任务：", description)
        print("工具：", tool_name)

        notify_progress(progress_callback, {
            "type": "step_started",
            "step": step_number,
            "total_steps": total_steps,
            "description": description,
            "tool": tool_name,
            "status": "running",
            "message": f"正在执行第 {step_number} 步"
        })

        try:
            if not tool_name:
                raise ValueError("当前步骤没有指定工具")

            arguments = generate_tool_arguments(step, results)

            print("工具参数：", arguments)

            authorization = permission_manager.authorize(
                tool_name,
                arguments
            )

            if not authorization.get("allowed"):

                step["status"] = authorization.get("status", "failed")
                message = authorization.get("message", "需要权限确认")

                results.append({
                    "step": step_number,
                    "success": False,
                    "status": step["status"],
                    "message": message,
                    "attempts": 0
                })

                save_task_progress(task_id, plan, "paused",result)

                notify_progress(progress_callback, {
                    "type": "step_paused",
                    "step": step_number,
                    "description": description,
                    "status": "paused",
                    "message": message
                })

                return {
                    "success": False,
                    "status": "paused",
                    "task": plan.get("task"),
                    "results": results
                }

            final_arguments = authorization.get("arguments", arguments)

            max_attempts = (
                MAX_RETRIES + 1
                if tool_name in RETRYABLE_TOOLS
                else 1
            )

            attempt_history = []
            tool_success = False
            tool_result = None

            for attempt in range(1, max_attempts + 1):

                print(
                    f"\n[小zzh] 第 {step_number} 步："
                    f"第 {attempt}/{max_attempts} 次尝试"
                )

                try:
                    retry_authorization = permission_manager.authorize(
                        tool_name,
                        dict(final_arguments)
                    )

                    if not retry_authorization.get("allowed"):

                        step["status"] = retry_authorization.get(
                            "status", "failed"
                        )

                        message = retry_authorization.get(
                            "message", "需要权限确认"
                        )

                        results.append({
                            "step": step_number,
                            "success": False,
                            "status": step["status"],
                            "message": message,
                            "attempts": attempt - 1,
                            "attempt_history": attempt_history
                        })

                        save_task_progress(task_id, plan, "paused",result)

                        notify_progress(progress_callback, {
                            "type": "step_paused",
                            "step": step_number,
                            "description": description,
                            "status": "paused",
                            "message": message
                        })

                        return {
                            "success": False,
                            "status": "paused",
                            "task": plan.get("task"),
                            "results": results
                        }

                    tool_result = execute_tool(
                        tool_name,
                        retry_authorization.get(
                            "arguments",
                            final_arguments
                        )
                    )

                    if not isinstance(tool_result, dict):
                        tool_result = {
                            "success": True,
                            "result": tool_result
                        }

                    if tool_result.get("success", True):
                        tool_success = True

                        attempt_history.append({
                            "attempt": attempt,
                            "success": True
                        })

                        print("[小zzh] 工具执行成功")
                        break

                    error_message = tool_result.get(
                        "error",
                        "工具返回执行失败"
                    )

                except Exception as e:
                    error_message = str(e)

                attempt_history.append({
                    "attempt": attempt,
                    "success": False,
                    "error": error_message
                })

                print("[小zzh] 执行失败：", error_message)

                if attempt < max_attempts:
                    print("[小zzh] 准备重新尝试...")

            if tool_success:

                step["status"] = "completed"

                step_result = {
                    "step": step_number,
                    "success": True,
                    "description": description,
                    "tool": tool_name,
                    "result": tool_result,
                    "attempts": len(attempt_history),
                    "attempt_history": attempt_history
                }

                results.append(step_result)

                save_task_progress(task_id, plan, "running",result)

                notify_progress(progress_callback, {
                    "type": "step_completed",
                    "step": step_number,
                    "total_steps": total_steps,
                    "description": description,
                    "tool": tool_name,
                    "status": "completed",
                    "result": tool_result,
                    "message": f"第 {step_number} 步执行成功"
                })

                print(f"[小zzh] 第 {step_number} 步执行成功")

            else:

                step["status"] = "failed"

                results.append({
                    "step": step_number,
                    "success": False,
                    "description": description,
                    "tool": tool_name,
                    "result": tool_result,
                    "attempts": len(attempt_history),
                    "attempt_history": attempt_history
                })

                save_task_progress(task_id, plan, "failed",result)

                notify_progress(progress_callback, {
                    "type": "step_failed",
                    "step": step_number,
                    "description": description,
                    "status": "failed",
                    "message": (
                        tool_result.get("error", "工具执行失败")
                        if isinstance(tool_result, dict)
                        else "工具执行失败"
                    )
                })

                break

        except Exception as e:

            step["status"] = "failed"

            results.append({
                "step": step_number,
                "success": False,
                "description": description,
                "error": str(e)
            })

            save_task_progress(task_id, plan, "failed",result)

            notify_progress(progress_callback, {
                "type": "step_failed",
                "step": step_number,
                "description": description,
                "status": "failed",
                "message": str(e)
            })

            print("[小zzh] 执行出错：", e)
            break

    all_completed = (
        all(item.get("success") for item in results)
        and len(results) == total_steps
    )

    final_status = "completed" if all_completed else "failed"

    save_task_progress(task_id, plan, final_status)

    report = {
        "success": all_completed,
        "status": final_status,
        "task": plan.get("task"),
        "results": results
    }

    notify_progress(progress_callback, {
        "type": "task_finished",
        "status": final_status,
        "success": all_completed,
        "message": (
            "所有任务步骤已完成"
            if all_completed
            else "任务执行结束，请查看执行报告"
        )
    })

    return report


def run_task(user_request: str, progress_callback=None):
    """规划任务、保存任务、执行任务并检查结果。"""

    print("\n[小zzh] 正在规划任务...")

    notify_progress(progress_callback, {
        "type": "planning",
        "status": "running",
        "message": "正在分析需求并规划任务"
    })

    plan_result = create_task_plan(user_request)

    if not plan_result.get("success"):
        error = plan_result.get("error", "任务规划失败")

        notify_progress(progress_callback, {
            "type": "task_error",
            "status": "failed",
            "message": error
        })

        return {
            "success": False,
            "error": error
        }

    plan = plan_result["plan"]

    print("\n[小zzh] 任务规划完成：")
    print(json.dumps(plan, ensure_ascii=False, indent=4))

    init_db()
    task_id = create_task(plan)

    print(f"\n[小zzh] 任务已保存，任务 ID：{task_id}")

    notify_progress(progress_callback, {
        "type": "plan_created",
        "task_id": task_id,
        "task": plan.get("task"),
        "total_steps": len(plan.get("steps", [])),
        "status": "running",
        "message": "任务计划已生成"
    })

    execution_report = execute_task_plan(
        plan,
        task_id=task_id,
        progress_callback=progress_callback
    )

    check_report = check_execution_result(
        execution_report,
        expected_steps=len(plan["steps"])
    )

    execution_status = execution_report.get("status")

    if execution_status == "paused":
        task_status = "paused"
    elif check_report.get("success"):
        task_status = "completed"
    else:
        task_status = "failed"

        final_report = {
        "success": check_report.get("success", False),
        "task_id": task_id,
        "task": plan.get("task"),
        "execution_report": execution_report,
        "check_report": check_report
    }

    # 将完整执行过程和最终报告写入任务计划
    plan["execution_report"] = execution_report
    plan["check_report"] = check_report
    plan["final_report"] = final_report

    # 最后统一保存完整任务数据
    update_task(task_id, plan, task_status)

    notify_progress(progress_callback, {
        "type": "report_ready",
        "status": task_status,
        "task_id": task_id,
        "message": "最终执行报告已生成",
        "report": final_report
    })

    print("\n========== 任务结果检查 ==========")
    print(json.dumps(
        check_report,
        ensure_ascii=False,
        indent=4,
        default=str
    ))

    return final_report


if __name__ == "__main__":

    request = input("请输入你希望小zzh完成的任务：").strip()

    if request:
        result = run_task(request)

        print("\n========== 最终执行报告 ==========")
        print(json.dumps(
            result,
            ensure_ascii=False,
            indent=4,
            default=str
        ))
