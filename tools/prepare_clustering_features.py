#!/usr/bin/env python3
"""Build compact feature vectors for music clustering from preview metrics."""

import argparse
import json
from pathlib import Path


CORE_CLUSTER_FEATURES = [
    "loudness_dbfs",
    "bass_ratio",
    "spectral_centroid_hz",
    "zero_crossing_rate",
    "onset_rate_per_sec",
    "silence_ratio",
    "rms_std",
    "crest_factor",
]

EXTENDED_PREVIEW_FEATURES = [
    "tempo",
    "energy",
    "bass",
    "brightness",
    "vocal",
    "dynamic",
    "intensity",
    "complexity",
    "tempo_bpm",
    "spectral_rolloff_85_hz",
    "spectral_flatness",
    "dynamic_range",
    "peak_amplitude",
    "mid_ratio",
    "high_ratio",
]

EXTENDED_ACOUSTICBRAINZ_FEATURES = [
    "danceability",
    "danceability_probability",
    "mood_happy",
    "mood_happy_probability",
    "mood_party",
    "mood_party_probability",
    "mood_relaxed",
    "mood_relaxed_probability",
    "mood_sad",
    "mood_sad_probability",
    "mood_aggressive",
    "mood_aggressive_probability",
    "mood_acoustic",
    "mood_acoustic_probability",
    "mood_electronic",
    "mood_electronic_probability",
    "voice_instrumental",
    "voice_instrumental_probability",
    "genre",
    "genre_probability",
]


def compute_stats(rows, feature_names):
    stats = {}
    for feature_name in feature_names:
        values = [row[feature_name] for row in rows]
        mean_value = sum(values) / len(values)
        variance = sum((value - mean_value) ** 2 for value in values) / len(values)
        std_value = variance ** 0.5
        stats[feature_name] = {
            "mean": mean_value,
            "std": std_value,
            "min": min(values),
            "max": max(values),
        }
    return stats


def zscore(value, mean_value, std_value):
    if std_value == 0:
        return 0.0
    return (value - mean_value) / std_value


def build_track_vector(track, feature_names, stats):
    preview_features = track["preview_features"]
    raw_features = {feature_name: preview_features[feature_name] for feature_name in feature_names}
    normalized_features = {
        feature_name: round(
            zscore(raw_features[feature_name], stats[feature_name]["mean"], stats[feature_name]["std"]),
            6,
        )
        for feature_name in feature_names
    }

    extended_preview = {
        feature_name: preview_features[feature_name]
        for feature_name in EXTENDED_PREVIEW_FEATURES
        if feature_name in preview_features
    }
    acousticbrainz_features = track.get("acousticbrainz", {})
    extended_acousticbrainz = {
        feature_name: acousticbrainz_features[feature_name]
        for feature_name in EXTENDED_ACOUSTICBRAINZ_FEATURES
        if feature_name in acousticbrainz_features
    }

    return {
        "id": track["id"],
        "title": track.get("title"),
        "artists": track.get("artists", []),
        "raw_features": raw_features,
        "normalized_features": normalized_features,
        "extended_preview_features": extended_preview,
        "extended_acousticbrainz_features": extended_acousticbrainz,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="final_dataset.json", help="Dataset JSON file")
    parser.add_argument(
        "--output",
        "-o",
        default="clustering_vectors.json",
        help="Output JSON file with clustering-ready vectors",
    )
    parser.add_argument(
        "--include-secondary",
        action="store_true",
        help="Include noisier experimental features such as tempo and rolloff",
    )
    args = parser.parse_args()

    dataset = json.loads(Path(args.input).read_text())
    selected_features = list(CORE_CLUSTER_FEATURES)
    if args.include_secondary:
        selected_features.extend(
            [feature_name for feature_name in EXTENDED_PREVIEW_FEATURES if feature_name not in selected_features]
        )

    tracks_with_preview = [
        track
        for track in dataset
        if "preview_features" in track
        and all(feature_name in track["preview_features"] for feature_name in selected_features)
    ]

    if not tracks_with_preview:
        raise ValueError("No tracks with the required preview features were found in the input dataset")

    rows = []
    for track in tracks_with_preview:
        rows.append({feature_name: track["preview_features"][feature_name] for feature_name in selected_features})

    stats = compute_stats(rows, selected_features)
    track_vectors = [build_track_vector(track, selected_features, stats) for track in tracks_with_preview]

    output_payload = {
        "source_file": args.input,
        "track_count": len(track_vectors),
        "core_features": list(CORE_CLUSTER_FEATURES),
        "extended_preview_features": list(EXTENDED_PREVIEW_FEATURES),
        "extended_acousticbrainz_features": list(EXTENDED_ACOUSTICBRAINZ_FEATURES),
        "selected_features": selected_features,
        "feature_notes": {
            "loudness_dbfs": "overall energy / level",
            "bass_ratio": "amount of low-end content",
            "spectral_centroid_hz": "brightness / spectral center of mass",
            "zero_crossing_rate": "noisiness / percussive texture proxy",
            "onset_rate_per_sec": "rhythmic activity / attack density",
            "silence_ratio": "sparsity and pauses",
            "rms_std": "variation of energy over time",
            "crest_factor": "transient punch vs sustained loudness",
            "tempo": "coarse speed score from preview analysis",
            "energy": "coarse energy score",
            "bass": "coarse low-end score",
            "brightness": "coarse treble presence score",
            "vocal": "coarse vocal presence score",
            "dynamic": "coarse dynamic score",
            "intensity": "coarse intensity score",
            "complexity": "coarse complexity score",
            "tempo_bpm": "tempo proxy, useful but less reliable on 30s previews",
            "spectral_rolloff_85_hz": "high-frequency extension",
            "spectral_flatness": "tonal vs noisy texture",
            "dynamic_range": "peak-to-peak amplitude spread",
            "peak_amplitude": "highest amplitude reached in the preview",
            "mid_ratio": "share of mid frequencies",
            "high_ratio": "share of high frequencies",
            "danceability": "AcousticBrainz danceability label",
            "voice_instrumental": "AcousticBrainz voice vs instrumental label",
            "genre": "AcousticBrainz genre guess",
        },
        "stats": stats,
        "tracks": track_vectors,
    }

    Path(args.output).write_text(json.dumps(output_payload, ensure_ascii=False, indent=2))

    print(f"Selected features: {', '.join(selected_features)}")
    print(f"Tracks exported: {len(track_vectors)}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()