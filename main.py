
import os
import sqlite3

from tools.ai_tools import ask_with_tools


# =========================
# 1. SQLite 记忆数据库
# =========================

ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, "memory.db")


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            )
        """)


# =========================
# 2. 读取历史聊天记录
# =========================

def load_history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT role, content
            FROM messages
            ORDER BY id DESC
            LIMIT 20
        """).fetchall()

    rows.reverse()

    return [
        {"role": role, "content": content}
        for role, content in rows
    ]


# =========================
# 3. 保存聊天记录
# =========================

def save_message(role, content):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO messages (role, content) VALUES (?, ?)",
            (role, content)
        )


# =========================
# 4. 启动 小zzh
# =========================

def main():
    init_db()

    history = load_history()

    print("=" * 40)
    print("小zzh 已启动！")
    print("输入 exit 退出程序")
    print("=" * 40)

    while True:
        user_text = input("\n你：").strip()

        if user_text.lower() in ["exit", "quit", "退出"]:
            print("小zzh：下次见！")
            break

        if not user_text:
            continue

        try:
            # AI 根据用户请求决定是否调用工具
            answer = ask_with_tools(
                user_request=user_text,
                history=history
            )

            print("\n小zzh：", answer)

            # 保存本轮对话
            save_message("user", user_text)
            save_message("assistant", answer)

            # 更新运行中的历史记录
            history.append({
                "role": "user",
                "content": user_text
            })

            history.append({
                "role": "assistant",
                "content": answer
            })

            history = history[-50:]

        except Exception as e:
            print("\n发生错误：", e)


if __name__ == "__main__":
    main()
