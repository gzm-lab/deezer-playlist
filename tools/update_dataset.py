#!/usr/bin/env python3
"""Incremental update: detect new/removed tracks and update dataset."""

import json
from pathlib import Path
import requests
import time
import sys
from core.audio_features import analyze_audio
from core.deezer_api import get_track_preview


def load_deezer_token():
    """Load cached Deezer token."""
    token_path = Path(".deezer_token.json")
    if token_path.exists():
        return json.loads(token_path.read_text())["access_token"]
    raise ValueError("No Deezer token found. Run python -m tools.deezer_latest_liked first")


def get_current_liked_tracks():
    """Get current list of liked tracks from Deezer."""
    token = load_deezer_token()
    tracks = []
    url = "https://api.deezer.com/user/me/tracks"

    while url:
        r = requests.get(url, params={"access_token": token}, timeout=20)
        r.raise_for_status()
        data = r.json()

        for item in data.get("data", []):
            tracks.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "artists": [item["artist"]["name"]],
                    "isrc": item.get("isrc"),
                }
            )

        url = data.get("next")
        time.sleep(0.03)

    return tracks


def main():
    print("🔄 Checking for updates...\n")

    dataset_path = Path("final_dataset.json")
    if not dataset_path.exists():
        print("❌ No final_dataset.json found. Run full pipeline first.")
        sys.exit(1)

    existing_dataset = json.loads(dataset_path.read_text())
    existing_ids = {track["id"] for track in existing_dataset}

    print(f"Current dataset: {len(existing_dataset)} tracks")

    print("Fetching current liked tracks from Deezer...")
    current_tracks = get_current_liked_tracks()
    current_ids = {track["id"] for track in current_tracks}

    print(f"Current liked tracks: {len(current_tracks)}")

    new_ids = current_ids - existing_ids
    removed_ids = existing_ids - current_ids

    print("\n📊 Changes detected:")
    print(f"   New tracks: {len(new_ids)}")
    print(f"   Removed tracks: {len(removed_ids)}")

    if not new_ids and not removed_ids:
        print("\n✅ No changes - dataset is up to date!")
        return

    if removed_ids:
        print(f"\n🗑️  Removing {len(removed_ids)} deleted tracks...")
        existing_dataset = [t for t in existing_dataset if t["id"] not in removed_ids]

        previews_dir = Path("previews")
        for track_id in removed_ids:
            preview_file = previews_dir / f"{track_id}.mp3"
            if preview_file.exists():
                preview_file.unlink()
                print(f"    🗑️  Deleted preview: {track_id}.mp3")

    if new_ids:
        print(f"\n➕ Processing {len(new_ids)} new tracks...")
        new_tracks = [t for t in current_tracks if t["id"] in new_ids]

        previews_dir = Path("previews")
        previews_dir.mkdir(exist_ok=True)

        for idx, track in enumerate(new_tracks, 1):
            track_id = track["id"]
            print(f"  {idx}/{len(new_ids)}: {track['title']} - {track['artists'][0]}")

            preview_url = get_track_preview(track_id)

            if preview_url:
                preview_path = previews_dir / f"{track_id}.mp3"

                try:
                    r = requests.get(preview_url, timeout=30)
                    r.raise_for_status()
                    preview_path.write_bytes(r.content)

                    features = analyze_audio(preview_path)
                    if features:
                        track["preview_features"] = features
                        print("    ✅ Analyzed")
                    else:
                        print("    ⚠️  Analysis failed")
                except Exception as e:
                    print(f"    ⚠️  Error: {e}")
            else:
                print("    ⚠️  No preview available")

            existing_dataset.append(track)
            time.sleep(0.05)

    dataset_path.write_text(json.dumps(existing_dataset, ensure_ascii=False, indent=2))

    print("\n✅ Dataset updated!")
    print(f"   Total tracks: {len(existing_dataset)}")
    print(f"   Added: {len(new_ids)}")
    print(f"   Removed: {len(removed_ids)}")

    if len(existing_dataset) > 0:
        with_features = sum(1 for t in existing_dataset if "preview_features" in t or "acousticbrainz" in t)
        print(f"   With audio features: {with_features} ({with_features/len(existing_dataset)*100:.1f}%)")


if __name__ == "__main__":
    main()