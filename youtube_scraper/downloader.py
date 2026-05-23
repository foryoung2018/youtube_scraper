import os
import yt_dlp

from .config import OUTPUT_DIR, OUTPUT_TEMPLATE


def download_video(url: str, output_dir: str | None = None) -> str:
    out = output_dir or OUTPUT_DIR
    os.makedirs(out, exist_ok=True)

    opts = {
        "outtmpl": os.path.join(out, OUTPUT_TEMPLATE),
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath


def download_best(url: str, output_dir: str | None = None) -> str:
    out = output_dir or OUTPUT_DIR
    os.makedirs(out, exist_ok=True)

    opts = {
        "outtmpl": os.path.join(out, OUTPUT_TEMPLATE),
        "format": "bestvideo*+bestaudio/best",
        "merge_output_format": "mp4",
        "quiet": False,
        "no_warnings": False,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        return filepath


def download_audio(url: str, output_dir: str | None = None) -> str:
    out = output_dir or OUTPUT_DIR
    os.makedirs(out, exist_ok=True)

    opts = {
        "outtmpl": os.path.join(out, "%(title)s.%(ext)s"),
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": False,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filepath = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filepath)
        return base + ".mp3"
