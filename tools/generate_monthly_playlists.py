#!/usr/bin/env python3
"""Generate rotating monthly playlists from clustered tracks and extended features."""

import argparse
import json
import random
from datetime import datetime
from pathlib import Path


PROFILE_ROTATION = [
    {
        "name": "bright_motion",
        "cluster_axis_preferences": ["spectral_centroid_hz", "onset_rate_per_sec", "rms_std"],
        "track_score_features": ["brightness", "energy", "onset_rate_per_sec", "mood_party_probability"],
    },
    {
        "name": "smooth_groove",
        "cluster_axis_preferences": ["bass_ratio", "crest_factor", "zero_crossing_rate"],
        "track_score_features": ["bass", "danceability_probability", "bass_ratio", "silence_ratio"],
    },
    {
        "name": "soft_air",
        "cluster_axis_preferences": ["silence_ratio", "loudness_dbfs", "crest_factor"],
        "track_score_features": ["silence_ratio", "crest_factor", "mood_relaxed_probability", "loudness_dbfs"],
    },
    {
        "name": "late_night_texture",
        "cluster_axis_preferences": ["zero_crossing_rate", "spectral_flatness", "spectral_centroid_hz"],
        "track_score_features": ["spectral_flatness", "zero_crossing_rate", "mood_sad_probability", "vocal"],
    },
    {
        "name": "warm_pop_front",
        "cluster_axis_preferences": ["loudness_dbfs", "rms_std", "spectral_centroid_hz"],
        "track_score_features": ["energy", "vocal", "mood_happy_probability", "loudness_dbfs"],
    },
]


def month_seed(month_key):
    return sum(ord(char) for char in month_key)


def track_score(track, feature_names):
    combined = {}
    combined.update(track.get("raw_features", {}))
    combined.update(track.get("extended_preview_features", {}))
    combined.update(track.get("extended_acousticbrainz_features", {}))

    total = 0.0
    matches = 0
    for feature_name in feature_names:
        value = combined.get(feature_name)
        if isinstance(value, (int, float)):
            total += float(value)
            matches += 1
        elif isinstance(value, str):
            total += 1.0 if value.startswith("not_") is False else 0.0
            matches += 1

    if matches == 0:
        return 0.0
    return total / matches


def cluster_fit(cluster, preferred_axes):
    axis_lookup = {axis["feature"]: abs(axis["value"]) for axis in cluster.get("top_axes", [])}
    return sum(axis_lookup.get(axis_name, 0.0) for axis_name in preferred_axes)


def build_track_lookup(vector_payload):
    return {track["id"]: track for track in vector_payload["tracks"]}


def load_history(history_path):
    path = Path(history_path)
    if not path.exists():
        return {"entries": []}
    return json.loads(path.read_text())


def save_history(history_path, history_payload):
    Path(history_path).write_text(json.dumps(history_payload, ensure_ascii=False, indent=2))


def recent_track_ids(history_payload, lookback_months):
    entries = history_payload.get("entries", [])
    recent_entries = entries[-lookback_months:] if lookback_months > 0 else entries
    track_ids = set()
    for entry in recent_entries:
        for playlist in entry.get("playlists", []):
            for track in playlist.get("tracks", []):
                track_ids.add(track["id"])
    return track_ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", default="clustering_vectors.json", help="Vector JSON file")
    parser.add_argument("--clusters", default="clusters.json", help="Cluster JSON file")
    parser.add_argument("--output", default="monthly_playlists.json", help="Output playlist JSON file")
    parser.add_argument("--month", default=datetime.now().strftime("%Y-%m"), help="Month key, e.g. 2026-04")
    parser.add_argument("--playlist-size", type=int, default=8, help="Tracks per generated playlist")
    parser.add_argument(
        "--history",
        default=None,
        help="Optional history JSON file used to avoid repeating tracks across months",
    )
    parser.add_argument(
        "--lookback-months",
        type=int,
        default=3,
        help="How many previous months to inspect when penalizing repeats",
    )
    parser.add_argument(
        "--repeat-penalty",
        type=float,
        default=25.0,
        help="Penalty subtracted from tracks already used in recent months",
    )
    args = parser.parse_args()

    vector_payload = json.loads(Path(args.vectors).read_text())
    cluster_payload = json.loads(Path(args.clusters).read_text())
    history_path = args.history or f"{Path(args.output).stem}_history.json"
    history_payload = load_history(history_path)
    recent_ids = recent_track_ids(history_payload, args.lookback_months)

    rng = random.Random(month_seed(args.month))
    track_lookup = build_track_lookup(vector_payload)

    playlists = []
    used_cluster_ids = set()
    for profile in PROFILE_ROTATION:
        ranked_clusters = sorted(
            cluster_payload["clusters"],
            key=lambda cluster: cluster_fit(cluster, profile["cluster_axis_preferences"]),
            reverse=True,
        )

        selected_cluster = None
        for candidate_cluster in ranked_clusters:
            candidate_tracks = candidate_cluster.get("tracks", [])
            if candidate_cluster["cluster_id"] not in used_cluster_ids and candidate_tracks:
                selected_cluster = candidate_cluster
                break
        if selected_cluster is None:
            selected_cluster = next((cluster for cluster in ranked_clusters if cluster.get("tracks")), ranked_clusters[0])

        used_cluster_ids.add(selected_cluster["cluster_id"])

        candidates = []
        for track_stub in selected_cluster["tracks"]:
            track = track_lookup.get(track_stub["id"])
            if not track:
                continue
            score = track_score(track, profile["track_score_features"])
            if track["id"] in recent_ids:
                score -= args.repeat_penalty
            jitter = rng.random() * 0.05
            candidates.append((score + jitter, track))

        candidates.sort(key=lambda item: item[0], reverse=True)
        selected_tracks = [
            {
                "id": track["id"],
                "title": track.get("title"),
                "artists": track.get("artists", []),
                "score": round(score, 4),
            }
            for score, track in candidates[: args.playlist_size]
        ]

        playlists.append(
            {
                "month": args.month,
                "profile": profile["name"],
                "source_cluster": selected_cluster["cluster_id"],
                "cluster_top_axes": selected_cluster["top_axes"],
                "track_score_features": profile["track_score_features"],
                "tracks": selected_tracks,
            }
        )

    output_payload = {
        "month": args.month,
        "history_file": history_path,
        "lookback_months": args.lookback_months,
        "playlist_count": len(playlists),
        "playlists": playlists,
    }
    Path(args.output).write_text(json.dumps(output_payload, ensure_ascii=False, indent=2))

    history_entries = [entry for entry in history_payload.get("entries", []) if entry.get("month") != args.month]
    history_entries.append({"month": args.month, "playlists": playlists})
    history_payload["entries"] = history_entries
    save_history(history_path, history_payload)

    print(f"Month: {args.month}")
    print(f"Playlists generated: {len(playlists)}")
    print(f"Output: {args.output}")
    print(f"History: {history_path}")
    for playlist in playlists:
        print(f"{playlist['profile']}: cluster={playlist['source_cluster']} tracks={len(playlist['tracks'])}")


if __name__ == "__main__":
    main()