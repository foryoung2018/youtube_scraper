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


def download_best(url: str, output_dir: str | None = None) -> tuple[str, str]:
    out = output_dir or OUTPUT_DIR
    os.makedirs(out, exist_ok=True)

    video_path = None
    audio_path = None

    video_opts = {
        "outtmpl": os.path.join(out, "%(title)s.%(ext)s"),
        "format": "bestvideo",
        "quiet": False,
        "no_warnings": False,
    }
    try:
        with yt_dlp.YoutubeDL(video_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
    except Exception as e:
        print(f"Video download failed: {e}")

    audio_opts = {
        "outtmpl": os.path.join(out, "%(title)s.%(ext)s"),
        "format": "bestaudio",
        "quiet": False,
        "no_warnings": False,
    }
    try:
        with yt_dlp.YoutubeDL(audio_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(info)
    except Exception as e:
        print(f"Audio download failed: {e}")

    return video_path, audio_path


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
