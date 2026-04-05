#!/usr/bin/env python3
"""Merge all feature sources into one final dataset."""

import argparse
import json
from pathlib import Path


def read_json_from_candidates(*paths):
    for path_str in paths:
        path = Path(path_str)
        if path.exists():
            return json.loads(path.read_text()), path
    raise FileNotFoundError(f"None of these files exist: {', '.join(paths)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--songs", default="all_songs.json", help="Source song export")
    parser.add_argument("--preview", default=None, help="Preview enrichment JSON file")
    parser.add_argument("--acousticbrainz", default=None, help="AcousticBrainz enrichment JSON file")
    parser.add_argument("--musicbrainz", default=None, help="MusicBrainz match JSON file")
    parser.add_argument("--output", default="final_dataset.json", help="Merged output JSON file")
    args = parser.parse_args()

    print("Loading data sources...")

    all_songs, songs_path = read_json_from_candidates(args.songs)

    preview_candidates = [args.preview] if args.preview else ["preview_enriched.json", "old/preview_enriched.json"]
    acousticbrainz_candidates = (
        [args.acousticbrainz] if args.acousticbrainz else ["acousticbrainz_enriched.json", "old/acousticbrainz_enriched.json"]
    )
    musicbrainz_candidates = [args.musicbrainz] if args.musicbrainz else ["musicbrainz_matched.json", "old/musicbrainz_matched.json"]

    preview_enriched, preview_path = read_json_from_candidates(*preview_candidates)
    acousticbrainz_enriched, acousticbrainz_path = read_json_from_candidates(*acousticbrainz_candidates)
    musicbrainz_matched, musicbrainz_path = read_json_from_candidates(*musicbrainz_candidates)

    print(f"Songs: {songs_path}")
    print(f"Preview: {preview_path}")
    print(f"AcousticBrainz: {acousticbrainz_path}")
    print(f"MusicBrainz: {musicbrainz_path}")

    preview_by_id = {s["id"]: s for s in preview_enriched}
    ab_by_id = {s["id"]: s for s in acousticbrainz_enriched}
    mb_by_id = {s["id"]: s for s in musicbrainz_matched}

    print(f"All songs: {len(all_songs)}")
    print(f"Preview features: {len(preview_by_id)}")
    print(f"AcousticBrainz features: {len(ab_by_id)}")
    print(f"MusicBrainz IDs: {len(mb_by_id)}")

    final_dataset = []

    for song in all_songs:
        track_id = song["id"]
        merged = {**song}

        if track_id in mb_by_id:
            merged["musicbrainz"] = mb_by_id[track_id].get("musicbrainz")

        if track_id in preview_by_id:
            merged["preview_features"] = preview_by_id[track_id].get("preview_features")

        if track_id in ab_by_id:
            merged["acousticbrainz"] = ab_by_id[track_id].get("acousticbrainz")

        final_dataset.append(merged)

    with_preview = sum(1 for s in final_dataset if "preview_features" in s)
    with_ab = sum(1 for s in final_dataset if "acousticbrainz" in s)
    with_both = sum(1 for s in final_dataset if "preview_features" in s and "acousticbrainz" in s)
    with_any_audio = sum(1 for s in final_dataset if "preview_features" in s or "acousticbrainz" in s)

    print("\n📊 Final dataset statistics:")
    print(f"Total tracks: {len(final_dataset)}")
    print(f"With preview features: {with_preview} ({with_preview/len(final_dataset)*100:.1f}%)")
    print(f"With AcousticBrainz: {with_ab} ({with_ab/len(final_dataset)*100:.1f}%)")
    print(f"With both: {with_both} ({with_both/len(final_dataset)*100:.1f}%)")
    print(f"With any audio features: {with_any_audio} ({with_any_audio/len(final_dataset)*100:.1f}%)")

    output_path = Path(args.output)
    output_path.write_text(json.dumps(final_dataset, ensure_ascii=False, indent=2))

    print(f"\n✅ Final dataset saved to: {output_path}")
    print(f"Size: {output_path.stat().st_size / (1024*1024):.1f} MB")


if __name__ == "__main__":
    main()