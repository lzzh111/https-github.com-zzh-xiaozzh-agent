
from tools import web_search

result = web_search(
    "今日ai新闻且是当天最新的" \
    "",
    max_results=10
)

if result["success"]:
    print("\n搜索成功！")
    print("关键词：", result["query"])
    print("结果数量：", result["count"])

    for index, item in enumerate(result["results"], 1):
        print(f"\n--- 搜索结果 {index} ---")
        print("标题：", item["title"])
        print("摘要：", item["snippet"])
        print("链接：", item["url"])

else:
    print("搜索失败：", result["error"])
