#!/usr/bin/env python3
"""Helper script to exercise yt-dlp's private _decrypt_nsig helper.

This script now only accepts a remote YouTube player URL and relies on yt-dlp to normalize JS.
"""

from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
YT_DLP_DIR = ROOT_DIR / "yt-dlp"
if str(YT_DLP_DIR) not in sys.path:
    sys.path.insert(0, str(YT_DLP_DIR))

from yt_dlp import YoutubeDL  # type: ignore  # noqa: E402
from yt_dlp.extractor.youtube import YoutubeIE  # type: ignore  # noqa: E402
from yt_dlp.utils import ExtractorError  # type: ignore  # noqa: E402


def validate_player_url(player_url: str) -> str:
    """僅允許傳遞 https://www.youtube.com/s/player/... 的 player JS URL"""
    pattern = r'^https://www\.youtube\.com/s/player/[A-Za-z0-9_\-]+/.+\.js$'
    if not re.match(pattern, player_url):
        raise SystemExit(
            '參數錯誤: --player 需為 https://www.youtube.com/s/player/.../base.js 類型的 URL')
    return player_url


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="YouTube nsig decoder (requires remote player URL)")
    parser.add_argument("--n", dest="n_value", required=True, help="The raw nsig value to decode")
    parser.add_argument(
        "--player",
        dest="player_url",
        required=True,
    help="Player JS URL (must be https://www.youtube.com/s/player/.../base.js)",
    )
    parser.add_argument(
        "--cachedir",
        default=None,
        help="Optional cache directory passed to YoutubeDL (default: disabled)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Dump full traceback even for extractor failures",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Enable extractor nsig trace logs (sets YT_DLP_NSIG_TRACE=1, adds --verbose)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    # 僅驗證 player URL，實際正規化交由 yt-dlp 處理
    processed_url = validate_player_url(args.player_url)

    opts = {
        "quiet": False,
        "cachedir": args.cachedir,
        "ratelimit": None,
    }

    # Optional tracing for step-by-step comparison
    if getattr(args, "trace", False):
        import os
        os.environ["YT_DLP_NSIG_TRACE"] = "1"
        opts["verbose"] = True

    ytdl = YoutubeDL(opts)
    youtube_ie = YoutubeIE(ytdl)

    version = getattr(__import__("yt_dlp.version").version, "__version__", "unknown")
    print(f"yt-dlp version: {version}")
    print(f"original URL : {args.player_url}")
    print(f"processed URL: {processed_url}")

    # Show n function name to aid debugging/verification
    try:
        jscode = youtube_ie._load_player('', processed_url)  # type: ignore[attr-defined]
        n_name = youtube_ie._extract_n_function_name(jscode, player_url=processed_url)  # type: ignore[attr-defined]
        print(f"n function name: {n_name}")
    except Exception as _e:  # non-fatal visibility helper
        if args.trace:
            print(f"n function name: <failed> ({_e})")
        else:
            print("n function name: <unavailable>")

    try:
        decrypted = youtube_ie._decrypt_nsig(args.n_value, "", processed_url)  # type: ignore[attr-defined]
    except ExtractorError as exc:  # yt-dlp specific failure
        print(f"ExtractorError: {exc}")
        if args.verbose:
            raise
        return 2
    except Exception as exc:  # pylint: disable=broad-except
        print(f"Unexpected error: {exc}")
        if args.verbose:
            raise
        return 3

    print(f"decoded nsig  : {decrypted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
