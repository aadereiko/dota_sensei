"""Steam CDN image paths.

OpenDota's constants return CDN-relative paths with a cache-busting query, e.g.
`/apps/dota2/images/dota_react/items/blink.png?t=1593393829403`.
"""

CDN_BASE = "https://cdn.cloudflare.steamstatic.com"


def cdn_image_url(path: str | None) -> str | None:
    """Absolute URL for a constants image path, or None."""
    if not path:
        return None
    return f"{CDN_BASE}{path}" if path.startswith("/") else path
