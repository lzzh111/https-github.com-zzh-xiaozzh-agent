
from tools.ai_tools import ask_with_tools


while True:
    user_input = input("\n你：")

    if user_input.lower() in ["exit", "quit", "退出"]:
        break

    answer = ask_with_tools(user_input)

    print("\nMyAgent：", answer)
