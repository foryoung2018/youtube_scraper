import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from youtube_scraper.discover import add_channel_to_author, discover_channels
from youtube_scraper.downloader import download_audio, download_best, download_video
from youtube_scraper.metadata import get_metadata
from youtube_scraper.search import get_playlist, list_authors, list_channel_videos, search


TYPE_TAGS = {
    "video": "[VIDEO]",
    "short": "[SHORT]",
    "members": "[MEMBERS]",
}


def _format_video(r: dict) -> str:
    tag = TYPE_TAGS.get(r.get("type", "video"), "[VIDEO]")
    views = f"{r['view_count']:,}" if r.get("view_count") else "N/A"
    date = r.get("upload_date", "N/A")
    return f"  {tag:<9} {r['title']}  |  {views} views  |  {date}  |  {r['url']}"


def main():
    parser = argparse.ArgumentParser(description="YouTube video scraper")
    sub = parser.add_subparsers(dest="command")

    info_parser = sub.add_parser("info", help="Get video metadata")
    info_parser.add_argument("url", help="YouTube video URL")

    download_parser = sub.add_parser("download", help="Download a video")
    download_parser.add_argument("url", help="YouTube video URL")
    download_parser.add_argument("-a", "--audio", action="store_true", help="Download audio only (mp3)")
    download_parser.add_argument("-o", "--output", help="Output directory")

    best_parser = sub.add_parser("best", help="Download video+audio separately at highest quality")
    best_parser.add_argument("url", help="YouTube video URL")
    best_parser.add_argument("-o", "--output", help="Output directory")

    search_parser = sub.add_parser("search", help="Search YouTube")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("-n", "--max-results", type=int, default=5, help="Max results (default: 5)")

    playlist_parser = sub.add_parser("playlist", help="List playlist videos")
    playlist_parser.add_argument("url", help="Playlist URL")

    channel_parser = sub.add_parser("channel", help="List recent videos from a channel")
    channel_parser.add_argument("channel", help="Channel name (@handle) or channel URL")
    channel_parser.add_argument("-n", "--max-results", type=int, default=5, help="Max results (default: 5)")
    channel_parser.add_argument("-d", "--detail", action="store_true", help="Show full metadata (views, dates) - slower")

    list_parser = sub.add_parser("list", help="List recent videos from monitored authors")
    list_parser.add_argument("-n", "--max-results", type=int, default=5, help="Max videos per channel (default: 5)")
    list_parser.add_argument("-f", "--file", default="author", help="Author file path (default: author)")
    list_parser.add_argument("-q", "--quick", action="store_true", help="Fast mode (less metadata, no view counts)")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show enrichment details (member filtering, dates)")

    discover_parser = sub.add_parser("discover", help="Discover new YouTube channels by describing your needs")
    discover_parser.add_argument("query", help="Describe what kind of content/creators you're looking for")
    discover_parser.add_argument("-n", "--max-results", type=int, default=10, help="Max recommendations (default: 10)")
    discover_parser.add_argument("-a", "--add", nargs="*", metavar="N", type=int, help="Add recommended channels to author file (e.g. -a 1 3 to add #1 and #3)")
    discover_parser.add_argument("-f", "--file", default="author", help="Author file path (default: author)")

    args = parser.parse_args()

    if args.command == "info":
        meta = get_metadata(args.url)
        print(json.dumps(meta, indent=2, ensure_ascii=False))

    elif args.command == "download":
        if args.audio:
            path = download_audio(args.url, args.output)
        else:
            path = download_video(args.url, args.output)
        print(f"Downloaded: {path}")

    elif args.command == "best":
        video_path, audio_path = download_best(args.url, args.output)
        if video_path:
            print(f"Video: {video_path}")
        if audio_path:
            print(f"Audio: {audio_path}")

    elif args.command == "search":
        results = search(args.query, args.max_results)
        for r in results:
            print(f"{r['title']}  |  {r['url']}")

    elif args.command == "playlist":
        results = get_playlist(args.url)
        for r in results:
            print(f"{r['title']}  |  {r['url']}")

    elif args.command == "channel":
        results = list_channel_videos(args.channel, args.max_results, include_shorts=True, detailed=args.detail)
        for r in results:
            print(_format_video(r))

    elif args.command == "list":
        videos_by_channel = list_authors(args.file, args.max_results, detailed=not args.quick, verbose=args.verbose)
        if not videos_by_channel:
            print(f"No channels found in author file: {args.file}")
        else:
            for channel, videos in videos_by_channel.items():
                print(f"\n{channel}:")
                for r in videos:
                    print(_format_video(r))

    elif args.command == "discover":
        results = discover_channels(args.query, args.max_results)
        if not results:
            print("No matching channels found.")
        else:
            print(f"\nRecommendations for: {args.query}\n")
            for i, r in enumerate(results, 1):
                score = r.get("score", 0)
                stars = "⭐" * min(int(score / 2) + 1, 5)
                print(f"  [{i}] {r.get('handle', '?')}  {stars}")
                print(f"      {r.get('title', '')}")
                print(f"      {r.get('reason', '')}")
                print()

            if args.add is not None and len(args.add) > 0:
                print("-" * 50)
                for n in args.add:
                    if 1 <= n <= len(results):
                        handle = results[n - 1].get("handle", "")
                        if handle:
                            add_channel_to_author(handle, args.file)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
