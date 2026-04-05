#!/usr/bin/env python3
"""Single entrypoint for dataset building, updates, clustering and playlists."""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PYTHON = sys.executable


def run_module(module_name, args=None):
    command = [PYTHON, "-m", module_name]
    if args:
        command.extend(args)

    print(f"\n==> Running {module_name}")
    subprocess.run(command, cwd=ROOT, check=True)


def build_dataset(skip_export=False):
    if not skip_export:
        run_module("tools.export_coup_de_coeur")

    run_module("tools.musicbrainz_enrich")
    run_module("tools.acousticbrainz_enrich")
    run_module("tools.full_preview_analysis")
    run_module("tools.merge_all_features")


def build_playlists(month, clusters, playlist_size, history, lookback_months, repeat_penalty):
    run_module("tools.prepare_clustering_features")
    run_module("tools.cluster_tracks", ["--clusters", str(clusters)])

    playlist_args = [
        "--month",
        month,
        "--playlist-size",
        str(playlist_size),
        "--history",
        history,
        "--lookback-months",
        str(lookback_months),
        "--repeat-penalty",
        str(repeat_penalty),
    ]
    run_module("tools.generate_monthly_playlists", playlist_args)


def update_dataset():
    run_module("tools.update_dataset")


def main():
    parser = argparse.ArgumentParser(description="Run the Deezer pipeline from one place.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_dataset_parser = subparsers.add_parser("build-dataset", help="Run the full dataset build pipeline")
    build_dataset_parser.add_argument(
        "--skip-export",
        action="store_true",
        help="Reuse the existing all_songs.json instead of exporting Deezer likes again",
    )

    subparsers.add_parser("update-dataset", help="Update final_dataset.json from Deezer changes")

    build_playlists_parser = subparsers.add_parser("build-playlists", help="Create vectors, clusters and monthly playlists")
    build_playlists_parser.add_argument("--month", required=True, help="Month key like 2026-04")
    build_playlists_parser.add_argument("--clusters", type=int, default=8, help="Number of clusters to build")
    build_playlists_parser.add_argument("--playlist-size", type=int, default=12, help="Tracks per playlist")
    build_playlists_parser.add_argument(
        "--history",
        default="monthly_playlists_history.json",
        help="History file used to rotate tracks across months",
    )
    build_playlists_parser.add_argument(
        "--lookback-months",
        type=int,
        default=3,
        help="How many previous months to inspect when penalizing repeats",
    )
    build_playlists_parser.add_argument(
        "--repeat-penalty",
        type=float,
        default=25.0,
        help="Penalty applied to recently used tracks",
    )

    build_all_parser = subparsers.add_parser("build-all", help="Build dataset, then clustering and playlists")
    build_all_parser.add_argument("--month", required=True, help="Month key like 2026-04")
    build_all_parser.add_argument("--skip-export", action="store_true", help="Reuse the existing all_songs.json")
    build_all_parser.add_argument("--clusters", type=int, default=8, help="Number of clusters to build")
    build_all_parser.add_argument("--playlist-size", type=int, default=12, help="Tracks per playlist")
    build_all_parser.add_argument(
        "--history",
        default="monthly_playlists_history.json",
        help="History file used to rotate tracks across months",
    )
    build_all_parser.add_argument(
        "--lookback-months",
        type=int,
        default=3,
        help="How many previous months to inspect when penalizing repeats",
    )
    build_all_parser.add_argument(
        "--repeat-penalty",
        type=float,
        default=25.0,
        help="Penalty applied to recently used tracks",
    )

    args = parser.parse_args()

    if args.command == "build-dataset":
        build_dataset(skip_export=args.skip_export)
        return

    if args.command == "update-dataset":
        update_dataset()
        return

    if args.command == "build-playlists":
        build_playlists(
            month=args.month,
            clusters=args.clusters,
            playlist_size=args.playlist_size,
            history=args.history,
            lookback_months=args.lookback_months,
            repeat_penalty=args.repeat_penalty,
        )
        return

    if args.command == "build-all":
        build_dataset(skip_export=args.skip_export)
        build_playlists(
            month=args.month,
            clusters=args.clusters,
            playlist_size=args.playlist_size,
            history=args.history,
            lookback_months=args.lookback_months,
            repeat_penalty=args.repeat_penalty,
        )


if __name__ == "__main__":
    main()