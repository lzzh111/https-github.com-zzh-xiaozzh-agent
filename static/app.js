
let currentMode = "chat";
let busy = false;
let activeTaskId = null;
let lastEventCount = 0;

const messages = document.getElementById("messages");
const input = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");



function setMode(mode) {
    currentMode = mode;

    const modes = {
        chat: {
            title: "普通对话",
            description: "和小zzh自由交流",
            placeholder: "给小zzh发送消息……"
        },
        task: {
            title: "自主任务",
            description: "让小zzh规划并实时执行任务",
            placeholder: "描述你希望小zzh完成的任务……"
        },
        history: {
            title: "历史任务中心",
            description: "查看和管理过去执行的任务",
            placeholder: ""
        }
    };

    document.getElementById("chatMode").classList.toggle(
        "active", mode === "chat"
    );

    document.getElementById("taskMode").classList.toggle(
        "active", mode === "task"
    );

    document.getElementById("historyMode").classList.toggle(
        "active", mode === "history"
    );

    const historyView = document.getElementById("historyView");
    const composer = document.getElementById("composer");

    const isHistory = mode === "history";

    messages.style.display = isHistory ? "none" : "block";
    historyView.style.display = isHistory ? "block" : "none";
    composer.style.display = isHistory ? "none" : "block";

    document.getElementById("modeTitle").textContent =
        modes[mode].title;

    document.getElementById("modeDescription").textContent =
        modes[mode].description;

    input.placeholder = modes[mode].placeholder;

    if (isHistory) {
        loadTasks();
    }
}



function addMessage(role, content) {
    document.getElementById("welcome")?.remove();

    const row = document.createElement("div");
    row.className = `message ${role}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "我" : "✦";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = content;

    if (role === "user") {
        row.appendChild(bubble);
    } else {
        row.appendChild(avatar);
        row.appendChild(bubble);
    }

    messages.appendChild(row);
    messages.scrollTop = messages.scrollHeight;

    return bubble;
}


function addTaskPanel(taskId) {
    document.getElementById("welcome")?.remove();

    const row = document.createElement("div");
    row.className = "message assistant";

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = "✦";

    const panel = document.createElement("div");
    panel.className = "bubble task-report";

    const title = document.createElement("h3");
    title.textContent = "小zzh 正在执行任务";

    const id = document.createElement("p");
    id.className = "task-meta";
    id.textContent = "任务编号：" + taskId;

    const status = document.createElement("div");
    status.className = "task-status running";
    status.textContent = "准备启动……";

    const progress = document.createElement("div");
    progress.className = "progress-track";

    const progressBar = document.createElement("div");
    progressBar.className = "progress-bar";
    progress.appendChild(progressBar);

    const steps = document.createElement("div");
    steps.className = "live-steps";

    const log = document.createElement("div");
    log.className = "live-log";

    panel.append(title, id, status, progress, steps, log);
    row.append(avatar, panel);
    messages.appendChild(row);

    messages.scrollTop = messages.scrollHeight;

    return {
        panel,
        status,
        progressBar,
        steps,
        log
    };
}


function addLog(target, message) {
    const item = document.createElement("p");
    item.textContent = message;
    target.appendChild(item);
    messages.scrollTop = messages.scrollHeight;
}


function addLiveStep(target, event) {
    const item = document.createElement("div");
    item.className = "task-step";

    const title = document.createElement("strong");
    title.textContent =
        `第 ${event.step} 步：${event.description || "执行任务"}`;

    const detail = document.createElement("p");
    detail.textContent = event.message || "正在处理……";

    item.append(title, detail);
    target.appendChild(item);

    messages.scrollTop = messages.scrollHeight;
    return item;
}


function formatResult(value) {
    if (typeof value === "string") return value;

    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}


function updateLiveStep(item, event) {
    const detail = item.querySelector("p");

    if (event.type === "step_completed") {
        item.classList.add("step-completed");
        detail.textContent = "✓ " + (event.message || "执行成功");

        if (event.result !== undefined) {
            const pre = document.createElement("pre");
            pre.textContent = formatResult(event.result);
            item.appendChild(pre);
        }

    } else if (event.type === "step_failed") {
        item.classList.add("step-failed");
        detail.textContent = "✕ " + (event.message || "执行失败");

    } else if (event.type === "step_paused") {
        item.classList.add("step-paused");
        detail.textContent = "⏸ " + (event.message || "等待权限确认");
    }

    messages.scrollTop = messages.scrollHeight;
}


async function pollTask(taskId, ui) {
    let finished = false;

    while (!finished) {
        try {
            const response = await fetch(
                `/api/task/progress/${encodeURIComponent(taskId)}`
            );

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "无法获取任务进度");
            }

            const events = data.events || [];

            while (lastEventCount < events.length) {
                const event = events[lastEventCount];
                lastEventCount++;

                if (event.type === "planning") {
                    ui.status.textContent = "正在规划任务……";
                    addLog(ui.log, event.message);

                } else if (event.type === "plan_created") {
                    ui.status.textContent = "任务计划已生成，准备执行";
                    addLog(ui.log, event.message);

                } else if (event.type === "task_started") {
                    ui.status.textContent = "任务执行中";
                    addLog(ui.log, event.message);

                } else if (event.type === "step_started") {
                    ui.status.textContent =
                        `正在执行第 ${event.step} 步`;

                    const item = addLiveStep(ui.steps, event);
                    ui.steps.dataset[`step${event.step}`] = "running";

                    if (!ui.stepItems) ui.stepItems = {};
                    ui.stepItems[event.step] = item;

                } else if (
                    event.type === "step_completed" ||
                    event.type === "step_failed" ||
                    event.type === "step_paused"
                ) {
                    const item = ui.stepItems?.[event.step];

                    if (item) {
                        updateLiveStep(item, event);
                    }

                    if (event.type === "step_completed") {
                        ui.status.textContent =
                            `第 ${event.step} 步已完成`;
                    } else if (event.type === "step_failed") {
                        ui.status.textContent = "任务步骤执行失败";
                    } else {
                        ui.status.textContent = "任务暂停，等待权限确认";
                    }

                } else if (event.type === "task_error") {
                    ui.status.textContent = "任务发生错误";
                    addLog(ui.log, event.message);

                } else if (event.type === "task_finished") {
                    ui.status.textContent =
                        event.status === "completed"
                            ? "所有步骤执行完成"
                            : "任务执行结束";

                    ui.progressBar.style.width =
                        event.status === "completed" ? "100%" : "0%";

                } else if (event.type === "report_ready") {
                    addLog(ui.log, event.message);
                }

                // 按已完成步骤数量更新进度条
                const completed = Object.values(
                    ui.stepItems || {}
                ).filter(item =>
                    item.classList.contains("step-completed")
                ).length;

                const total = Math.max(
                    events.find(e => e.total_steps)?.total_steps || 1,
                    completed
                );

                ui.progressBar.style.width =
                    `${Math.min(100, completed / total * 100)}%`;
            }

            if (data.finished) {
                finished = true;

                const report = data.report;

                if (report) {
                    showFinalReport(ui, report);
                }
            }

        } catch (error) {
            ui.status.textContent = "获取进度失败：" + error.message;
            finished = true;
        }

        if (!finished) {
            await new Promise(resolve => setTimeout(resolve, 800));
        }
    }
}


function showFinalReport(ui, report) {
    const execution = report.execution_report || {};
    const status = execution.status || (
        report.success ? "completed" : "failed"
    );

    const labels = {
        completed: "执行完成",
        failed: "执行失败",
        paused: "等待权限确认"
    };

    ui.status.textContent = labels[status] || status;
    ui.status.className = "task-status " + status;

    if (status === "completed") {
        ui.progressBar.style.width = "100%";
    }

    const summary = document.createElement("div");
    summary.className = "final-summary";

    const heading = document.createElement("h4");
    heading.textContent = "最终执行报告";

    const content = document.createElement("pre");
    content.textContent = formatResult(report);

    summary.append(heading, content);
    ui.panel.appendChild(summary);

    messages.scrollTop = messages.scrollHeight;
}


async function startTask(text) {
    const response = await fetch("/api/task/start", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            message: text
        })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
        throw new Error(data.error || "任务启动失败");
    }

    activeTaskId = data.task_id;
    lastEventCount = 0;

    const ui = addTaskPanel(activeTaskId);

    await pollTask(activeTaskId, ui);
}


async function sendMessage() {
    const text = input.value.trim();

    if (!text || busy) return;

    busy = true;
    sendButton.disabled = true;
    sendButton.textContent = "处理中…";

    addMessage("user", text);
    input.value = "";

    try {
        if (currentMode === "task") {
            await startTask(text);

        } else {
            const loading = addMessage(
                "assistant",
                "小zzh 正在思考……"
            );

            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    message: text
                })
            });

            const data = await response.json();

            if (!response.ok || !data.success) {
                throw new Error(data.error || "请求失败");
            }

            loading.textContent = data.answer;
        }

    } catch (error) {
        addMessage("assistant", "发生错误：" + error.message);

    } finally {
        busy = false;
        sendButton.disabled = false;
        sendButton.textContent = "发送 ↑";
        input.focus();
    }
}


function clearConversation() {
    messages.innerHTML = `
        <div class="welcome" id="welcome">
            <div class="welcome-icon">✦</div>
            <h1>你好，我是小zzh</h1>
            <p>你的个人 AI 助手。</p>
        </div>
    `;
}


input.addEventListener("keydown", function(event) {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
});


async function loadHistory() {
    try {
        const response = await fetch("/api/history");
        const data = await response.json();

        if (data.success && data.history.length > 0) {
            document.getElementById("welcome")?.remove();

            for (const item of data.history) {
                addMessage(
                    item.role === "user" ? "user" : "assistant",
                    item.content
                );
            }
        }
    } catch (error) {
        console.error("读取历史记录失败：", error);
    }
}


loadHistory();

// ================================
// V5：历史任务中心
// ================================

let taskPage = 1;
let taskLimit = 10;
let taskTotalPages = 0;
let taskKeyword = "";
let taskStatusFilter = "all";

const taskList = document.getElementById("taskList");
const taskSearch = document.getElementById("taskSearch");
const taskStatus = document.getElementById("taskStatus");
const taskPagination = document.getElementById("taskPagination");
const taskDetail = document.getElementById("taskDetail");
const taskDetailContent = document.getElementById("taskDetailContent");


// 状态中文名称
function getTaskStatusLabel(status) {
    const labels = {
        pending: "待执行",
        running: "执行中",
        completed: "已完成",
        failed: "执行失败",
        paused: "已暂停"
    };

    return labels[status] || status || "未知状态";
}


// 安全生成 HTML 元素
function createTaskElement(tag, className, content) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (content !== undefined) {
        element.textContent = content;
    }

    return element;
}


// 获取历史任务
async function loadTasks() {
    taskList.textContent = "正在加载历史任务……";
    taskPagination.innerHTML = "";

    try {
        const params = new URLSearchParams({
            status: taskStatusFilter,
            keyword: taskKeyword,
            page: taskPage,
            limit: taskLimit
        });

        const response = await fetch(
            `/api/tasks?${params.toString()}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "获取任务失败");
        }

        taskList.innerHTML = "";

        const tasks = data.tasks || [];

        taskTotalPages = data.total_pages || 0;
        taskPage = data.page || 1;

        if (tasks.length === 0) {
            taskList.appendChild(
                createTaskElement(
                    "p",
                    "empty-state",
                    "没有找到符合条件的历史任务"
                )
            );

        } else {
            tasks.forEach(task => {
                renderTaskItem(task);
            });
        }

        renderTaskPagination(data);

    } catch (error) {
        taskList.textContent = "加载失败：" + error.message;
        console.error("历史任务加载失败：", error);
    }
}


// 渲染单个任务
function renderTaskItem(task) {
    const card = createTaskElement("div", "history-task-card");

    const header = createTaskElement("div", "history-task-header");

    const name = createTaskElement(
        "strong",
        "history-task-name",
        task.task_name || "未命名任务"
    );

    const status = createTaskElement(
        "span",
        "task-status " + task.status,
        getTaskStatusLabel(task.status)
    );

    header.append(name, status);

    const meta = createTaskElement(
        "p",
        "task-meta",
        "创建时间：" + (task.created_at || "未知")
    );

    const id = createTaskElement(
        "p",
        "task-meta",
        "任务 ID：" + task.task_id
    );

    const detailButton = createTaskElement(
        "button",
        "task-detail-button",
        "查看详情 →"
    );

    detailButton.type = "button";

    detailButton.addEventListener("click", () => {
        loadTaskDetail(task.task_id);
    });

    card.append(header, meta, id, detailButton);

    taskList.appendChild(card);
}


// 渲染分页
function renderTaskPagination(data) {
    taskPagination.innerHTML = "";

    const total = data.total || 0;
    const current = data.page || 1;
    const totalPages = data.total_pages || 0;

    const info = createTaskElement(
        "span",
        "pagination-info",
        `共 ${total} 条任务，第 ${current} / ${totalPages} 页`
    );

    const previous = createTaskElement(
        "button",
        "",
        "上一页"
    );

    previous.disabled = current <= 1;

    previous.addEventListener("click", () => {
        if (taskPage > 1) {
            taskPage--;
            loadTasks();
        }
    });

    const next = createTaskElement(
        "button",
        "",
        "下一页"
    );

    next.disabled = current >= totalPages;

    next.addEventListener("click", () => {
        if (taskPage < taskTotalPages) {
            taskPage++;
            loadTasks();
        }
    });

    taskPagination.append(info, previous, next);
}


// 搜索和筛选
function searchTasks() {
    taskKeyword = taskSearch.value.trim();
    taskStatusFilter = taskStatus.value;

    taskPage = 1;

    loadTasks();
}


// 查询任务详情
async function loadTaskDetail(taskId) {
    taskDetail.style.display = "block";
    taskDetailContent.textContent = "正在加载任务详情……";

    try {
        const response = await fetch(
            `/api/tasks/${encodeURIComponent(taskId)}`
        );

        const data = await response.json();

        if (!response.ok || !data.success) {
            throw new Error(data.error || "获取任务详情失败");
        }

        renderTaskDetail(data.task);

        taskDetail.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    } catch (error) {
        taskDetailContent.textContent =
            "加载任务详情失败：" + error.message;
    }
}


// 渲染任务详情
function renderTaskDetail(task) {
    taskDetailContent.innerHTML = "";

    const title = createTaskElement(
        "h3",
        "",
        task.task_name || "未命名任务"
    );

    const status = createTaskElement(
        "span",
        "task-status " + task.status,
        getTaskStatusLabel(task.status)
    );

    const id = createTaskElement(
        "p",
        "task-meta",
        "任务 ID：" + task.task_id
    );

    const created = createTaskElement(
        "p",
        "task-meta",
        "创建时间：" + task.created_at
    );

    const updated = createTaskElement(
        "p",
        "task-meta",
        "更新时间：" + task.updated_at
    );

    const heading = createTaskElement(
        "h4",
        "",
        "任务执行计划"
    );

    const plan = createTaskElement("pre", "task-plan");

    plan.textContent = formatResult(task.plan || {});

    taskDetailContent.append(
        title,
        status,
        id,
        created,
        updated,
        heading,
        plan
    );
}


// 关闭任务详情
function closeTaskDetail() {
    taskDetail.style.display = "none";
    taskDetailContent.innerHTML = "";
}


// 搜索按钮
taskSearch.addEventListener("keydown", event => {
    if (event.key === "Enter") {
        searchTasks();
    }
});

taskStatus.addEventListener("change", () => {
    searchTasks();
});


// 页面初始化时隐藏历史任务区域
document.getElementById("historyView").style.display = "none";
taskDetail.style.display = "none";
