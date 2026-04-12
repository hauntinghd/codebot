import requests
import os

def web_search(query: str, max_results: int = 3) -> str:
    """
    Perform a web search using DuckDuckGo Instant Answer API (no key required, privacy-friendly).
    Returns a string summary of the top results.
    """
    try:
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_redirect=1&no_html=1"
        resp = requests.get(url, timeout=10)
        data = resp.json()
        results = []
        if 'AbstractText' in data and data['AbstractText']:
            results.append(data['AbstractText'])
        if 'RelatedTopics' in data:
            for topic in data['RelatedTopics']:
                if isinstance(topic, dict) and 'Text' in topic:
                    results.append(topic['Text'])
                if len(results) >= max_results:
                    break
        if not results:
            results.append('No relevant web results found.')
        return '\n'.join(results[:max_results])
    except Exception as e:
        return f"[Web search failed: {e}]"
