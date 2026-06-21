import re
import httpx


def detect_source_type(url: str) -> tuple[str, str]:
    """
    Détecte le type de source et retourne (type, rss_url).
    """
    url = url.strip()

    # YouTube channel ou @handle
    youtube_patterns = [
        r'youtube\.com/@([\w-]+)',
        r'youtube\.com/channel/([\w-]+)',
        r'youtube\.com/user/([\w-]+)',
        r'youtube\.com/c/([\w-]+)',
    ]
    for pattern in youtube_patterns:
        match = re.search(pattern, url)
        if match:
            identifier = match.group(1)
            # Si c'est un @handle, on doit résoudre le channel_id
            if url.count('@') > 0 and 'channel/' not in url:
                rss_url = f"https://www.youtube.com/feeds/videos.xml?user={identifier}"
            else:
                rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={identifier}"
            return "youtube", rss_url

    # Reddit subreddit
    reddit_match = re.search(r'reddit\.com/r/([\w-]+)', url)
    if reddit_match:
        subreddit = reddit_match.group(1)
        rss_url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=week"
        return "reddit", rss_url

    # GitHub releases
    github_match = re.search(r'github\.com/([\w-]+)/([\w-]+)', url)
    if github_match:
        owner = github_match.group(1)
        repo = github_match.group(2)
        rss_url = f"https://github.com/{owner}/{repo}/releases.atom"
        return "github", rss_url

    # Hacker News keyword
    if 'news.ycombinator.com' in url or url.startswith('hn:'):
        keyword = url.replace('hn:', '').strip()
        rss_url = f"https://hnrss.org/newest?q={keyword}&points=10"
        return "hackernews", rss_url

    # RSS/Atom par défaut
    return "rss", url


async def validate_rss_url(url: str) -> bool:
    """Vérifie que l'URL RSS est accessible."""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=10, follow_redirects=True)
            return resp.status_code == 200
    except Exception:
        return False