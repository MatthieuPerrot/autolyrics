"""Search backends with automatic fallback"""


class SearchBackend:
    """Base class for search backends"""

    def search(self, query: str, num_results: int = 5) -> list[str]:
        """
        Search for a query and return URLs.

        Args:
            query: Search query string
            num_results: Maximum number of results to return

        Returns:
            List of URLs as strings

        Raises:
            Exception: If search fails
        """
        raise NotImplementedError

    def name(self) -> str:
        """Return backend name for logging"""
        return self.__class__.__name__


class DuckDuckGoBackend(SearchBackend):
    """DuckDuckGo search - free, no API key required"""

    def search(self, query: str, num_results: int = 5) -> list[str]:
        try:
            from ddgs import DDGS
        except ImportError:
            # Fallback to old package name
            from duckduckgo_search import DDGS

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
            return [r['href'] for r in results]


class GoogleScraperBackend(SearchBackend):
    """Google search via web scraping - free but can be rate limited"""

    def search(self, query: str, num_results: int = 5) -> list[str]:
        from googlesearch import search as google_search

        # googlesearch returns generator, convert to list
        return list(google_search(query, num_results=num_results, lang='en'))


class GoogleCSEBackend(SearchBackend):
    """Google Custom Search Engine - requires API key"""

    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx

    def search(self, query: str, num_results: int = 5) -> list[str]:
        from googleapiclient.discovery import build

        service = build("customsearch", "v1", developerKey=self.api_key)
        res = service.cse().list(q=query, cx=self.cx, num=num_results).execute()

        return [item["link"] for item in res.get("items", [])]


class BraveSearchBackend(SearchBackend):
    """Brave Search API - requires API key, 2000 free requests/month"""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, num_results: int = 5) -> list[str]:
        import requests

        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": self.api_key}
        params = {"q": query, "count": num_results}

        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()

        data = response.json()
        return [item['url'] for item in data.get('web', {}).get('results', [])]
