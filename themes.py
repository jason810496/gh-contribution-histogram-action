from __future__ import annotations

import json
import os

import requests

THEME_URI = "https://raw.githubusercontent.com/anuraghazra/github-readme-stats/refs/heads/master/themes/index.js"
THEME_CACHE_JSON = "themes.json"


class Theme:
    """
    A class to represent a theme.
    """

    # attributes
    title_color: str
    icon_color: str
    text_color: str
    bg_color: str
    background_color: str
    border_color: str | None = None

    def __init__(
        self,
        title_color: str,
        icon_color: str,
        text_color: str,
        bg_color: str,
        background_color: str,
        border_color: str | None = None,
    ):
        self.title_color = title_color
        self.icon_color = icon_color
        self.text_color = text_color
        self.bg_color = bg_color
        self.background_color = background_color
        self.border_color = border_color


def get_themes() -> dict[str, Theme]:
    """
    Fetch the themes from the GitHub repository.
    """
    if os.path.exists(THEME_CACHE_JSON):
        print(f"Loading themes from cache: {THEME_CACHE_JSON}")
        with open(THEME_CACHE_JSON, "r") as f:
            result = json.load(f)
            return {k: Theme(**v) for k, v in result.items()}

    print(f"Fetching themes from {THEME_URI}...")
    response = requests.get(THEME_URI)
    if response.status_code != 200:
        raise Exception(
            f"Failed to fetch themes: {response.status_code} - {response.text}"
        )

    # Extract the themes from the response text
    themes_text = response.text.split("themes = {")[1].split("};")[0]

    # Parse themes into a dictionary
    result = {}

    # Split by theme blocks
    theme_blocks = themes_text.split("},")
    for block in theme_blocks:
        if not block.strip():
            continue

        # Extract theme name
        theme_parts = block.strip().split(":", 1)
        if len(theme_parts) < 2:
            continue

        theme_name = theme_parts[0].strip().strip("\"'")
        theme_data = theme_parts[1].strip().lstrip("{").strip()

        # Parse attributes
        attrs = {}
        for line in theme_data.split(","):
            line = line.strip()
            if not line or "//" in line:  # Skip comments
                continue

            key_value = line.split(":", 1)
            if len(key_value) < 2:
                continue

            key = key_value[0].strip().strip("\"'")
            value = key_value[1].strip().strip("\"',")

            # Skip comments that might be on the same line
            if "//" in value:
                value = value.split("//")[0].strip().strip("\"',")

            attrs[key] = f"#{value}"

        # Create Theme object
        try:
            # Map to Theme attributes
            bg_color = attrs.get("bg_color", "")
            theme_obj = Theme(
                title_color=attrs.get("title_color", ""),
                icon_color=attrs.get("icon_color", ""),
                text_color=attrs.get("text_color", ""),
                bg_color=bg_color,
                background_color=bg_color,  # Use bg_color as background_color
                border_color=attrs.get("border_color"),
            )
            result[theme_name] = theme_obj
        except Exception as e:
            print(f"Error parsing theme {theme_name}: {e}")

    # set cache
    with open(THEME_CACHE_JSON, "w") as f:
        json.dump({k: v._asdict() for k, v in result.items()}, f, indent=4)
        print(f"Cached themes to {THEME_CACHE_JSON}")
    # return the themes
    print(f"Fetched {len(result)} themes from {THEME_URI}")
    return result


if __name__ == "__main__":
    themes = get_themes()
    # Print the themes
    print(themes)
