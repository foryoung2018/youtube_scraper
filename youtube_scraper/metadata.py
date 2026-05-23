import yt_dlp


def get_video_info(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def get_metadata(url: str) -> dict:
    info = get_video_info(url)
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "like_count": info.get("like_count"),
        "upload_date": info.get("upload_date"),
        "uploader": info.get("uploader"),
        "channel_url": info.get("channel_url"),
        "thumbnail": info.get("thumbnail"),
        "categories": info.get("categories"),
        "tags": info.get("tags"),
    }
