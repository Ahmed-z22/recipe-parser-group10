import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

DEFAULT_TIMEOUT = 25


def get_recipe_data(url: str):
    """
    Route to a site-specific scraper based on the recipe domain.

    Returns:
        ({"title": str|None}, {"ingredients": list[str]}, {"directions": list[str]})
    """
    domain = urlparse(url).netloc.lower()

    if "allrecipes.com" in domain:
        return get_recipe_data_allrecipes(url)
    elif "epicurious.com" in domain:
        return get_recipe_data_epicurious(url)
    elif "bonappetit.com" in domain:
        return get_recipe_data_bonappetit(url)
    else:
        raise ValueError(
            f"Unsupported website domain: {domain}. "
            "Currently supported: allrecipes.com, epicurious.com, bonappetit.com"
        )

def _http_get_soup(url: str) -> BeautifulSoup:
    resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=DEFAULT_TIMEOUT)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "lxml")

