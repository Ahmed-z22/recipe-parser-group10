import json
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import html

SUPPORTED_WEBSITES = ["allrecipes.com", "epicurious.com", "bonappetit.com"]


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
            - {"title": str}: The recipe title (name).
            - {"ingredients": list[str]}: A list of ingredients.
            - {"directions": list[str]}: A list of cooking directions.
    Raises:
        ValueError: If the URL domain is unsupported or recipe data cannot be extracted.
    """
    domain = urlparse(url).netloc.lower()

    if domain.removeprefix("www.") not in SUPPORTED_WEBSITES:
        raise ValueError(
            f"Unsupported website domain: {domain}. "
            "Currently supported: allrecipes.com, epicurious.com, bonappetit.com"
        )

    soup = _http_get_soup(url)
    title, ingredients, directions = _extract_json_ld_recipe(soup, url, domain)
    return {"title": title}, {"ingredients": ingredients}, {"directions": directions}


def _http_get_soup(url: str) -> BeautifulSoup:
    """
    Sends an HTTP GET request and parses the response into a BeautifulSoup object.
    Args:
        url (str): The target URL (recipe page).
    Returns:
        BeautifulSoup: Parsed HTML content of the page.
    Raises:
        requests.HTTPError: If the HTTP request fails (e.g., 404, 500).
    """
    response = requests.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "lxml")


def _extract_json_ld_recipe(
    soup: BeautifulSoup, url: str, domain: str
) -> tuple[str | None, list[str], list[str]]:
    """
    Extracts recipe information (title, ingredients, and directions)
    from JSON-LD <script> blocks embedded in the HTML.
    Args:
        soup (BeautifulSoup): Parsed HTML content.
        url (str): The recipe page URL (used for error context).
        domain (str): The website domain (used for error context).
    Returns:
        tuple[str, list[str], list[str]]: A tuple containing:
            - The recipe title.
            - A list of ingredients.
            - A list of directions.
    Raises:
        ValueError: If no valid recipe data (title, ingredients, or directions) can be extracted.
    """
    title: str = ""
    ingredients: list[str] = []
    directions: list[str] = []

    # Iterate over all JSON-LD script tags, looking for Recipe data
    for script_tag in soup.select('script[type="application/ld+json"]'):
        raw = script_tag.string
        if not raw:
            continue

        try:
            # Try parsing the JSON inside the script tag
            data = json.loads(raw)
        except Exception:
            # Skip malformed or non-JSON script blocks
            continue

        # Ensure we have a list of JSON-LD objects to process
        blocks = data if isinstance(data, list) else [data]

        for block in blocks:
            if not isinstance(block, dict):
                continue

            block_type = block.get("@type")

            # Check if this JSON block is of type "Recipe" (can be string, list, or nested object)
            is_recipe = (
                (isinstance(block_type, str) and block_type == "Recipe")
                or (isinstance(block_type, list) and "Recipe" in block_type)
                or ("Recipe" in str(block_type))
            )

            if not is_recipe:
                continue

            # if current block is a Recipe, extract title, ingredients, and directions
            if not title:
                name = block.get("name")
                if isinstance(name, str) and name.strip():
                    title = name.strip()

            # Extract ingredients usually as a list of strings
            recipe_ingredients = block.get("recipeIngredient")
            if isinstance(recipe_ingredients, list):
                ingredients = [
                    str(s).strip() for s in recipe_ingredients if str(s).strip()
                ]

            # Extract cooking directions, can be a list of dicts or plain strings
            instructions = block.get("recipeInstructions")

            if isinstance(instructions, list):
                for step in instructions:
                    # Handle dict-based steps (common JSON-LD pattern)
                    if isinstance(step, dict):
                        text = step.get("text")
                        if isinstance(text, str) and text.strip():
                            directions.append(text.strip())
                    # Handle plain string steps
                    elif isinstance(step, str) and step.strip():
                        directions.append(step.strip())

            # Some pages store directions as a single string separated by newlines
            elif isinstance(instructions, str) and instructions.strip():
                parts = [p.strip() for p in instructions.split("\n") if p.strip()]
                directions.extend(parts)

            # Early exit
            if ingredients or directions:
                break

    # Final validation: ensure we have non-empty title, ingredients, and directions
    if not title or not ingredients or not directions:
        raise ValueError(
            f"Failed to extract recipe data from this website: {domain}.\n"
            f"Check the URL: {url} and confirm if it is a valid recipe page."
        )

    # make sure to strip any leading/trailing whitespace, and make all strings small case
    title = title.strip()
    ingredients = [html.unescape(ing.strip().lower()) for ing in ingredients]
    directions = [html.unescape(dir.strip().lower()) for dir in directions]

    return title, ingredients, directions
