
from ddgs import DDGS


def web_search(query: str, max_results: int = 5) -> dict:
    """
    搜索互联网，返回标题、摘要和链接。
    """

    try:
        query = query.strip()

        if not query:
            return {
                "success": False,
                "error": "搜索关键词不能为空"
            }

        # 限制每次最多返回 8 条
        max_results = max(1, min(int(max_results), 8))

        search_engine = DDGS()

        results = search_engine.text(
            query,
            max_results=max_results
        )

        formatted_results = []

        for item in results:
            formatted_results.append({
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "snippet": item.get("body", "")
            })

        return {
            "success": True,
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
