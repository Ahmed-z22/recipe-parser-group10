import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

def get_recipe_data(url: str):
    """
    Extracts recipe data (title, ingredients, and directions) from a supported recipe URL.

    Supported domains:
        - allrecipes.com
        - epicurious.com
        - bonappetit.com

    Args:
        url (str): The full URL of the recipe page.

    Returns:
        tuple[dict, dict, dict]: A tuple containing:
            - {"title": str | None}: The recipe title (or None if unavailable).
            - {"ingredients": list[str]}: A list of ingredients.
            - {"directions": list[str]}: A list of cooking directions.

    Raises:
        ValueError: If the URL domain is unsupported or recipe data cannot be extracted.
    """
    domain = urlparse(url).netloc.lower()

    if "allrecipes.com" in domain or "epicurious.com" in domain or "bonappetit.com" in domain:
        soup = _http_get_soup(url)
        title, ingredients, directions = _extract_json_ld_recipe(soup, url, domain)
        return {"title": title}, {"ingredients": ingredients}, {"directions": directions}
    else:
        raise ValueError(
            f"Unsupported website domain: {domain}. "
            "Currently supported: allrecipes.com, epicurious.com, bonappetit.com"
        )

def _http_get_soup(url: str) -> BeautifulSoup:
    """
    Sends an HTTP GET request and parses the response into a BeautifulSoup object.

    Args:
        url (str): The target URL.

    Returns:
        BeautifulSoup: Parsed HTML content of the page.

    Raises:
        requests.HTTPError: If the HTTP request fails (e.g., 404, 500).
    """
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")

def _extract_json_ld_recipe(soup: BeautifulSoup, url: str, domain: str) -> tuple[str | None, list[str], list[str]]:
    """
    Extracts recipe information (title, ingredients, and directions)
    from JSON-LD <script> blocks embedded in the HTML.

    Args:
        soup (BeautifulSoup): Parsed HTML content.
        url (str): The recipe page URL (used for error context).
        domain (str): The website domain (used for error context).

    Returns:
        tuple[str | None, list[str], list[str]]: A tuple containing:
            - The recipe title (or None if unavailable).
            - A list of ingredients.
            - A list of directions.

    Raises:
        ValueError: If no valid recipe data (title, ingredients, or directions) can be extracted.
    """
    title: str = ""
    ingredients: list[str] = []
    directions: list[str] = []

    for script_tag in soup.select('script[type="application/ld+json"]'):
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

            if not title:
                name = block.get("name")
                if isinstance(name, str) and name.strip():
                    title = name.strip()

            recipe_ingredients = block.get("recipeIngredient")
            if isinstance(recipe_ingredients, list):
                ingredients = [str(s).strip() for s in recipe_ingredients if str(s).strip()]

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

            if ingredients or directions:
                break

    if not title or not ingredients or not directions:
        raise ValueError(
            f"Failed to extract recipe data from {domain} page, possibly due to site structure changes.\n"
            f"Check the URL: {url}"
        )

    return title, ingredients, directions
