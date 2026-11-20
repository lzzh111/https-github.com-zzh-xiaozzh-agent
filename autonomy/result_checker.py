
def check_execution_result(report, expected_steps=None):
    """
    检查任务执行报告，判断任务是否真正完成。
    不会自动重复执行工具，避免重复操作。
    """

    if not isinstance(report, dict):
        return {
            "success": False,
            "status": "invalid",
            "message": "执行报告格式错误",
            "failed_steps": []
        }

    results = report.get("results", [])

    if not isinstance(results, list):
        return {
            "success": False,
            "status": "invalid",
            "message": "执行结果列表格式错误",
            "failed_steps": []
        }

    failed_steps = []
    completed_steps = []

    for item in results:
        if not isinstance(item, dict):
            failed_steps.append({
                "step": "unknown",
                "reason": "步骤结果格式错误"
            })
            continue

        if item.get("success") is True:
            completed_steps.append(item.get("step"))
        else:
            failed_steps.append({
                "step": item.get("step"),
                "reason": (
                    item.get("error")
                    or item.get("message")
                    or item.get("status")
                    or "执行失败"
                )
            })

    # 检查是否有步骤没有执行
    if expected_steps is not None:
        if len(results) < expected_steps:
            for number in range(len(results) + 1, expected_steps + 1):
                failed_steps.append({
                    "step": number,
                    "reason": "该步骤尚未执行"
                })

    if report.get("status") == "paused":
        status = "paused"
        message = "任务因权限或其他原因暂停，需要用户处理"

    elif failed_steps:
        status = "incomplete"
        message = "任务没有全部完成，请检查失败步骤"

    elif report.get("success") is True:
        status = "completed"
        message = "所有任务步骤均已成功执行"

    else:
        status = "incomplete"
        message = "任务执行状态未能确认"

    return {
        "success": status == "completed",
        "status": status,
        "message": message,
        "completed_steps": completed_steps,
        "failed_steps": failed_steps
    }


if __name__ == "__main__":

    test_report = {
        "success": True,
        "status": "completed",
        "results": [
            {"step": 1, "success": True},
            {"step": 2, "success": True},
            {"step": 3, "success": True}
        ]
    }

    result = check_execution_result(
        test_report,
        expected_steps=3
    )

    print("执行结果检查：")
    print(result)
