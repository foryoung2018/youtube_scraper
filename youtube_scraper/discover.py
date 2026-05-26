import json
import os
import sys

import yt_dlp

from .config import DISCOVER_MAX_RESULTS, LLM_API_KEY, LLM_BASE_URL, LLM_MODEL


def _log(msg: str):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def _get_channel_info(handle_or_url: str) -> dict | None:
    """Extract channel description, subscriber count, etc."""
    if handle_or_url.startswith("http"):
        url = handle_or_url
    elif handle_or_url.startswith("@"):
        url = f"https://www.youtube.com/{handle_or_url}"
    else:
        url = f"https://www.youtube.com/@{handle_or_url}"

    opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlistend": 0}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        return {
            "handle": handle_or_url if handle_or_url.startswith("@") else f"@{handle_or_url}",
            "title": info.get("title") or info.get("channel") or info.get("uploader") or handle_or_url,
            "description": (info.get("description") or "")[:500],
            "subscriber_count": info.get("channel_follower_count"),
            "channel_url": info.get("channel_url") or info.get("uploader_url") or url,
        }
    except Exception:
        return None


def _search_channels(query: str, max_results: int) -> list[dict]:
    """Search YouTube for channels matching the query in multiple ways."""
    seen = set()
    channels = []

    def _add_from_entries(entries):
        for entry in entries:
            uploader = entry.get("uploader") or entry.get("channel")
            uploader_url = entry.get("uploader_url") or entry.get("channel_url") or ""
            uploader_id = entry.get("uploader_id") or entry.get("channel_id")
            channel_id = entry.get("channel_id")

            if not uploader or not uploader_id:
                continue

            key = uploader_id
            if key in seen:
                continue
            seen.add(key)

            handle = None
            if uploader_url:
                parts = uploader_url.rstrip("/").split("/")
                if parts:
                    raw = parts[-1]
                    if raw.startswith("@"):
                        handle = raw
                    elif not raw.startswith("UC"):
                        handle = f"@{raw}"

            channels.append({
                "title": uploader.encode("utf-8", errors="replace").decode("utf-8"),
                "handle": handle or f"@{uploader_id}",
                "channel_id": channel_id or uploader_id,
                "uploader_id": uploader_id,
                "url": uploader_url or f"https://www.youtube.com/{handle or uploader_id}",
            })

    opts = {"quiet": True, "no_warnings": True, "extract_flat": True}

    # Search 1: standard YouTube search
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        _add_from_entries(result.get("entries", []))
    except Exception as e:
        _log(f"  Search 1 error: {e}")

    # Search 2: try "channels" search variant
    if len(channels) < max_results:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(f"ytsearch{max_results}:channel {query}", download=False)
            _add_from_entries(result.get("entries", []))
        except Exception as e:
            _log(f"  Search 2 error: {e}")

    return channels[:max_results * 2]


def _analyze_with_llm(user_query: str, channels: list[dict]) -> list[dict] | None:
    """Use LLM to analyze and rank channels. Returns None if LLM unavailable."""
    if not LLM_API_KEY:
        return None

    channel_list = []
    for i, c in enumerate(channels):
        subs = c.get("subscriber_count", "")
        subs_str = f"{subs:,}" if isinstance(subs, (int, float)) and subs else str(subs) if subs else "unknown"
        channel_list.append({
            "id": i + 1,
            "handle": c.get("handle", ""),
            "name": c.get("title", ""),
            "description": (c.get("description") or "no description")[:300],
            "subscribers": subs_str,
        })

    prompt = f"""You are a YouTube channel discovery assistant. A user wants to find channels matching:
"{user_query}"

Candidate channels from YouTube search:
{json.dumps(channel_list, ensure_ascii=False, indent=2)}

Analyze each one and recommend those that BEST match the user's needs. Return a JSON array sorted by relevance (best first), max 10 items. Each item must have:
- "handle": channel handle (@xxx)
- "title": channel name
- "reason": 1-2 sentence explanation in Chinese
- "score": 1-10 relevance score

Return ONLY valid JSON array, no other text."""

    import requests

    try:
        resp = requests.post(
            f"{LLM_BASE_URL}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {LLM_API_KEY}",
            },
            json={
                "model": LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            },
            timeout=90,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])
        return json.loads(content)
    except Exception as e:
        _log(f"  [WARN] LLM analysis failed: {e}")
        return None


def discover_channels(
    query: str,
    max_results: int = 10,
) -> list[dict]:
    """Search channels, enrich info, analyze with LLM, return recommendations."""
    limit = max_results or DISCOVER_MAX_RESULTS
    fetch = max(limit * 3, 25)

    _log(f"  Step 1/3: Searching YouTube for '{query}'...")
    candidates = _search_channels(query, fetch)
    _log(f"          Found {len(candidates)} unique channels")

    if not candidates:
        return []

    _log(f"  Step 2/3: Fetching channel details...")
    enrich_total = min(len(candidates), max(limit * 2, 20))
    enriched = []
    for i, c in enumerate(candidates[:enrich_total]):
        handle_or_url = c.get("handle") or c.get("url") or c.get("uploader_id", "")
        info = _get_channel_info(handle_or_url)
        if info:
            c["title"] = info.get("title") or c.get("title")
            c["handle"] = info.get("handle") or c.get("handle")
            c["description"] = info.get("description", "")
            c["subscriber_count"] = info.get("subscriber_count")
        else:
            c["description"] = ""
            c["subscriber_count"] = None
        enriched.append(c)
        _log(f"          [{i + 1}/{enrich_total}] {c.get('handle', '?')} - {c.get('title', '?')}")

    if LLM_API_KEY:
        _log(f"  Step 3/3: AI analysis ({LLM_MODEL})...")
        results = _analyze_with_llm(query, enriched[:limit * 2])
        if results:
            _log(f"          AI recommended {len(results)} channels")
            return results[:limit]
        _log(f"          AI failed, using enriched search results")

    # Fallback: return enriched channels sorted by subscriber count
    enriched.sort(key=lambda x: x.get("subscriber_count") or 0, reverse=True)
    output = []
    for c in enriched[:limit]:
        subs = c.get("subscriber_count")
        subs_str = f"{subs:,} subscribers" if subs else "unknown subscribers"
        output.append({
            "handle": c.get("handle", "?"),
            "title": c.get("title", "?"),
            "reason": f"{subs_str}. {(c.get('description', ''))[:100]}",
            "score": 0,
        })
    return output


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
