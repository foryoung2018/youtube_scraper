import json
import os
import sys

import yt_dlp

from .config import DISCOVER_MAX_RESULTS, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def _log(msg: str):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _get_channel_info(channel_handle: str) -> dict | None:
    """Extract channel description, subscriber count, etc."""
    url = f"https://www.youtube.com/{channel_handle}"
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlistend": 0}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            "handle": channel_handle,
            "title": info.get("title") or info.get("channel") or info.get("uploader") or channel_handle,
            "description": (info.get("description") or "")[:500],
            "subscriber_count": info.get("channel_follower_count"),
            "channel_url": info.get("channel_url") or info.get("uploader_url") or url,
        }
    except Exception:
        return None


def _search_channels(query: str, max_results: int) -> list[dict]:
    """Search YouTube for channels matching the query."""
    search_query = f"ytsearch{max_results}:{query}"
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    channels = []
    seen = set()

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(search_query, download=False)
        for entry in result.get("entries", []):
            uploader = entry.get("uploader")
            uploader_url = entry.get("uploader_url") or ""
            channel_id = entry.get("channel_id")
            uploader_id = entry.get("uploader_id")

            if not uploader:
                continue

            key = uploader_id or channel_id or uploader
            if key in seen:
                continue
            seen.add(key)

            handle = None
            if uploader_url:
                parts = uploader_url.rstrip("/").split("/")
                if parts:
                    handle = parts[-1]

            channels.append({
                "title": uploader,
                "handle": f"@{handle}" if handle and handle.startswith("@") is False and "/@" not in uploader_url else (handle or uploader),
                "channel_id": channel_id,
                "uploader_id": uploader_id,
                "url": uploader_url,
            })

            if len(channels) >= max_results * 2:
                break
    except Exception as e:
        _log(f"  Search error: {e}")

    return channels[:max_results * 2]


def _analyze_with_llm(user_query: str, channels: list[dict]) -> list[dict]:
    """Use LLM to analyze and rank channels based on user requirements."""
    if not LLM_API_KEY:
        _log("  [WARN] No OPENAI_API_KEY set, returning raw search results")
        return [{"handle": c["handle"], "title": c["title"], "reason": "raw search match"} for c in channels[:10]]

    channel_list = []
    for i, c in enumerate(channels):
        channel_list.append({
            "id": i + 1,
            "handle": c.get("handle"),
            "name": c.get("title"),
            "description": (c.get("description") or "")[:300],
            "subscribers": c.get("subscriber_count"),
        })

    prompt = f"""You are a YouTube channel discovery assistant. A user wants to find channels matching this description:

"{user_query}"

Below are {len(channel_list)} candidate channels found via YouTube search. Analyze each one and recommend the ones that BEST match the user's requirements. Consider:
- Topic relevance to the query
- Content quality and professionalism
- Language match (Chinese/English etc based on query context)
- Activity level and subscriber count

Return a JSON array of recommended channels (up to 10), sorted by relevance (best first). For each channel include:
- "handle": the channel handle (e.g. "@xxx")
- "title": channel name
- "reason": 1-2 sentence explanation in Chinese why this channel matches the user's needs
- "score": 1-10 relevance score

Channel candidates:
{json.dumps(channel_list, ensure_ascii=False, indent=2)}

Return ONLY valid JSON array, no other text."""

    import requests

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LLM_API_KEY}",
    }

    body = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
    }

    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=body,
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()

        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        return json.loads(content)
    except Exception as e:
        _log(f"  [WARN] LLM analysis failed: {e}, returning raw results")
        return [{"handle": c["handle"], "title": c["title"], "reason": "raw search match", "score": 0} for c in channels[:10]]


def discover_channels(
    query: str,
    max_results: int = 10,
    enrich: bool = True,
) -> list[dict]:
    """Main entry: search channels and analyze with LLM."""
    limit = max_results or DISCOVER_MAX_RESULTS
    fetch = max(limit * 3, 20)

    _log(f"  Searching YouTube for: {query}")
    candidates = _search_channels(query, fetch)
    _log(f"  Found {len(candidates)} unique channels in search results")

    if not candidates:
        _log("  No channels found.")
        return []

    if enrich and LLM_API_KEY:
        _log(f"  Enriching channel info for top {min(len(candidates), 15)} candidates...")
        enriched = []
        for c in candidates[:15]:
            handle = c.get("handle", "")
            if handle and not handle.startswith("http"):
                clean_handle = handle.lstrip("@")
                info = _get_channel_info(f"@{clean_handle}")
                if info:
                    c["description"] = info.get("description")
                    c["subscriber_count"] = info.get("subscriber_count")
                    c["title"] = info.get("title") or c.get("title")
            enriched.append(c)
            if len(enriched) >= 12:
                break
        candidates = enriched

    if LLM_API_KEY:
        _log(f"  Analyzing with LLM ({LLM_MODEL})...")
        results = _analyze_with_llm(query, candidates)
        _log(f"  LLM returned {len(results)} recommendations")
        return results[:limit]

    return [{"handle": c["handle"], "title": c["title"], "reason": "search match", "score": 0} for c in candidates[:limit]]


def add_channel_to_author(handle: str, author_file: str = "author") -> None:
    """Add a channel @handle to the author file if not already present."""
    if not handle.startswith("@"):
        handle = f"@{handle}"

    existing = []
    if os.path.isfile(author_file):
        with open(author_file, "r", encoding="utf-8") as f:
            content = f.read()
        existing = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    if handle in existing:
        _log(f"  {handle} already in {author_file}")
        return

    existing.append(handle)
    with open(author_file, "w", encoding="utf-8") as f:
        for h in existing:
            f.write(f"{h}\n")
    _log(f"  Added {handle} to {author_file}")
