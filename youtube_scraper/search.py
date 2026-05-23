import os
import sys

import yt_dlp

from .config import MAX_DOWNLOADS


def _log(msg: str):
    sys.stderr.write(msg + "\n")
    sys.stderr.flush()


def search(query: str, max_results: int | None = None) -> list[dict]:
    limit = max_results or MAX_DOWNLOADS
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "force_generic_extractor": False,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        result = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    entries = result.get("entries", [])
    return [
        {
            "id": e.get("id"),
            "title": e.get("title"),
            "duration": e.get("duration"),
            "view_count": e.get("view_count"),
            "uploader": e.get("uploader"),
            "url": f"https://www.youtube.com/watch?v={e.get('id')}",
        }
        for e in entries
    ]


def _resolve_channel_url(channel: str) -> str | None:
    if channel.startswith("http"):
        return channel
    if channel.startswith("@"):
        return f"https://www.youtube.com/{channel}/videos"
    return None


def _resolve_channel_base(channel: str) -> str | None:
    url = _resolve_channel_url(channel)
    if not url:
        return None
    return url.rstrip("/").removesuffix("/videos")


def _get_channel_id(channel: str) -> str | None:
    base = _resolve_channel_base(channel)
    if not base:
        return None
    try:
        opts = {"quiet": True, "no_warnings": True, "extract_flat": True, "playlistend": 0}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(base, download=False)
        return info.get("channel_id")
    except Exception:
        return None


def _get_uploads_playlist(channel: str) -> str | None:
    channel_id = _get_channel_id(channel)
    if not channel_id:
        return None
    if channel_id.startswith("UC"):
        playlist_id = "UU" + channel_id[2:]
    else:
        playlist_id = "UU" + channel_id
    return f"https://www.youtube.com/playlist?list={playlist_id}"


def _extract_entries(tab_url: str, limit: int, flat: bool = True) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": flat,
        "playlistend": limit,
    }
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            result = ydl.extract_info(tab_url, download=False)
        return result.get("entries", [])
    except Exception:
        return []


def _build_entry(e: dict, video_type: str = "video") -> dict:
    entry_id = e.get("id")
    raw_url = e.get("url") or ""
    is_short_url = "/shorts/" in raw_url
    is_short_duration = (
        e.get("duration") is not None
        and e.get("duration") > 0
        and e.get("duration") <= 120
    )
    if video_type == "video" and (is_short_url or is_short_duration):
        detected_type = "short"
    elif video_type == "short":
        detected_type = "short"
    else:
        detected_type = "video"

    availability = e.get("availability") or ""
    if "subscriber" in availability.lower() or "premium" in availability.lower():
        detected_type = "members"

    if detected_type == "short":
        url = f"https://www.youtube.com/shorts/{entry_id}"
    else:
        url = e.get("webpage_url") or e.get("original_url") or f"https://www.youtube.com/watch?v={entry_id}"

    return {
        "id": entry_id,
        "title": e.get("title"),
        "duration": e.get("duration"),
        "view_count": e.get("view_count"),
        "upload_date": e.get("upload_date"),
        "url": url,
        "type": detected_type,
    }


def _enrich_one(video: dict, idx: int, total: int, verbose: bool = False) -> dict:
    opts = {"quiet": True, "no_warnings": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video["url"], download=False)
        video["view_count"] = info.get("view_count")
        video["upload_date"] = info.get("upload_date")
        video["duration"] = info.get("duration") or video.get("duration")
        video["title"] = info.get("title") or video["title"]
        availability = info.get("availability") or ""
        if "subscriber" in availability.lower() or "premium" in availability.lower():
            video["type"] = "members"
            _log(f"    [{idx}/{total}] SKIP (members) {video['title'][:60]}")
        else:
            _log(f"    [{idx}/{total}] OK   {video.get('upload_date','?')}  {video.get('view_count','?')}  {video['title'][:60]}")
    except Exception as e:
        _log(f"    [{idx}/{total}] ERR  {video['url'][:60]}: {e}")
    return video


def _enrich_until(items: list[dict], target: int, verbose: bool = False) -> list[dict]:
    result = []
    idx = 0
    for item in items:
        idx += 1
        _enrich_one(item, idx, len(items), verbose=verbose)
        if item.get("type") != "members":
            result.append(item)
        if len(result) >= target:
            break
    return result


def list_channel_videos(
    channel: str, max_results: int | None = None, include_shorts: bool = False, detailed: bool = False, verbose: bool = False
) -> list[dict]:
    limit = max_results or MAX_DOWNLOADS
    fetch_limit = max(limit * 3, 15)

    channel_url = _resolve_channel_url(channel)
    if not channel_url:
        _log(f"  [{channel}] FAILED to resolve channel URL")
        return []

    # Use uploads playlist (includes ALL public uploads, unlike /videos tab)
    uploads_url = _get_uploads_playlist(channel)
    if not uploads_url:
        _log(f"  [{channel}] FAILED to get uploads playlist")
        return []

    if verbose:
        _log(f"  [{channel}] => {channel_url}")
        _log(f"  [{channel}] fetching uploads playlist (flat, limit={fetch_limit})...")

    entries = _extract_entries(uploads_url, fetch_limit, flat=True)
    seen_ids = set()
    videos = []
    for e in entries:
        entry = _build_entry(e, "video")
        if entry["id"] in seen_ids:
            continue
        seen_ids.add(entry["id"])
        videos.append(entry)

    if verbose:
        _log(f"  [{channel}] got {len(videos)} entries from uploads playlist")

    shorts = []
    if include_shorts:
        base_url = _resolve_channel_base(channel)
        if base_url:
            shorts_url = f"{base_url}/shorts"
            if verbose:
                _log(f"  [{channel}] fetching /shorts tab...")
            short_entries = _extract_entries(shorts_url, fetch_limit, flat=True)
            for e in short_entries:
                entry = _build_entry(e, "short")
                if entry["id"] in seen_ids:
                    continue
                seen_ids.add(entry["id"])
                shorts.append(entry)
            if verbose:
                _log(f"  [{channel}] got {len(shorts)} new shorts from /shorts tab")

    if detailed:
        if verbose:
            _log(f"  [{channel}] enriching videos (need {limit} non-member)...")
        videos = _enrich_until(videos, limit, verbose=verbose)
        if verbose and shorts:
            _log(f"  [{channel}] enriching shorts (need {limit} non-member)...")
        shorts = _enrich_until(shorts, limit, verbose=verbose)

    merged = videos + shorts
    merged.sort(key=lambda x: x.get("upload_date") or "", reverse=True)
    return merged[:limit]


def list_authors(
    author_file: str = "author", max_results: int | None = None, detailed: bool = True, verbose: bool = False
) -> dict[str, list[dict]]:
    if not os.path.isfile(author_file):
        _log(f"Author file not found: {author_file}")
        return {}

    with open(author_file, "r", encoding="utf-8") as f:
        channels = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

    if verbose:
        _log(f"Loaded {len(channels)} channel(s) from {author_file}: {', '.join(channels)}")
        _log("")

    result = {}
    for channel in channels:
        videos = list_channel_videos(channel, max_results, include_shorts=True, detailed=detailed, verbose=verbose)
        if videos:
            result[channel] = videos
        if verbose:
            _log("")

    return result


def get_playlist(url: str) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        result = ydl.extract_info(url, download=False)

    entries = result.get("entries", [])
    return [
        {
            "id": e.get("id"),
            "title": e.get("title"),
            "url": f"https://www.youtube.com/watch?v={e.get('id')}",
        }
        for e in entries
    ]
