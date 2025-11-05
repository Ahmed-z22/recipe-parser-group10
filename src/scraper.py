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


def _extract_json_ld_recipe(soup: BeautifulSoup) -> tuple[str | None, list[str], list[str]]:
    """
    Attempts to extract (title, ingredients, directions) from JSON-LD <script> blocks.
    Returns (None, [], []) if no usable Recipe block is found.
    """
    title: str | None = None
    ingredients: list[str] = []
    directions: list[str] = []

    for script_tag in soup.select('script[type="application/ld+json"]'):
        # Some sites include multiple JSON objects/arrays per <script>
        raw = script_tag.string
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except Exception:
            continue

        blocks = data if isinstance(data, list) else [data]
        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("@type")
            is_recipe = (
                isinstance(block_type, str) and block_type == "Recipe"
            ) or (isinstance(block_type, list) and "Recipe" in block_type) or ("Recipe" in str(block_type))

            if not is_recipe:
                continue

            # Title
            if not title:
                name = block.get("name")
                if isinstance(name, str) and name.strip():
                    title = name.strip()

            # Ingredients
            recipe_ingredients = block.get("recipeIngredient")
            if isinstance(recipe_ingredients, list):
                ingredients = [str(s).strip() for s in recipe_ingredients if str(s).strip()]

            # Directions / Instructions
            instructions = block.get("recipeInstructions")
            if isinstance(instructions, list):
                for step in instructions:
                    if isinstance(step, dict):
                        text = step.get("text")
                        if isinstance(text, str) and text.strip():
                            directions.append(text.strip())
                    elif isinstance(step, str) and step.strip():
                        directions.append(step.strip())
            elif isinstance(instructions, str) and instructions.strip():
                parts = [p.strip() for p in instructions.split("\n") if p.strip()]
                directions.extend(parts)

            # Found a usable Recipe block; early exit
            if ingredients or directions:
                return title, ingredients, directions

    return title, ingredients, directions

def get_recipe_data_allrecipes(
    url: str,
) -> tuple[dict[str, str | None], dict[str, list[str]], dict[str, list[str]]]:
    """
    Scrape an AllRecipes recipe page.

    Returns:
        (
          {"title": str|None},
          {"ingredients": list[str]},
          {"directions": list[str]},
        )
    """
    soup = _http_get_soup(url)

    title, ingredients, directions = _extract_json_ld_recipe(soup)

    # Fallbacks if JSON-LD is incomplete or missing
    if not title:
        headline = soup.select_one("h1.headline, h1")
        if headline:
            text = headline.get_text(strip=True)
            if text:
                title = text

    if not ingredients:
        ingredients = [
            node.get_text(strip=True)
            for node in soup.select(
                ".ingredients-item .ingredients-item-name, [data-component='Ingredient']"
            )
            if node.get_text(strip=True)
        ]

    if not directions:
        directions = [
            node.get_text(strip=True)
            for node in soup.select(
                ".instructions-section-item p, .recipe-directions__list--item"
            )
            if node.get_text(strip=True)
        ]

    return ({"title": title}, {"ingredients": ingredients}, {"directions": directions})
