#!/usr/bin/env python3
"""Cluster track vectors with a lightweight numpy k-means implementation."""

import argparse
import json
from pathlib import Path

import numpy as np


def build_matrix(tracks, feature_names):
    return np.array(
        [[track["normalized_features"][feature_name] for feature_name in feature_names] for track in tracks],
        dtype=np.float64,
    )


def kmeans(matrix, cluster_count, iterations=50, seed=42):
    if len(matrix) < cluster_count:
        raise ValueError("cluster_count cannot exceed the number of tracks")

    rng = np.random.default_rng(seed)
    centroids = matrix[rng.choice(len(matrix), size=cluster_count, replace=False)].copy()
    labels = np.zeros(len(matrix), dtype=np.int64)

    for _ in range(iterations):
        distances = np.linalg.norm(matrix[:, None, :] - centroids[None, :, :], axis=2)
        new_labels = np.argmin(distances, axis=1)

        if np.array_equal(labels, new_labels):
            break

        labels = new_labels
        for cluster_index in range(cluster_count):
            cluster_points = matrix[labels == cluster_index]
            if len(cluster_points) == 0:
                centroids[cluster_index] = matrix[rng.integers(0, len(matrix))]
            else:
                centroids[cluster_index] = cluster_points.mean(axis=0)

    return labels, centroids


def top_axes(centroid, feature_names, top_n=3):
    ranked_indices = np.argsort(np.abs(centroid))[::-1][:top_n]
    return [
        {
            "feature": feature_names[index],
            "value": round(float(centroid[index]), 4),
        }
        for index in ranked_indices
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", default="clustering_vectors.json", help="Input vector JSON file")
    parser.add_argument("--output", "-o", default="clusters.json", help="Output cluster JSON file")
    parser.add_argument("--clusters", "-k", type=int, default=4, help="Number of clusters")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text())
    tracks = payload["tracks"]
    feature_names = payload["selected_features"]
    matrix = build_matrix(tracks, feature_names)

    labels, centroids = kmeans(matrix, args.clusters, seed=args.seed)

    cluster_payload = {
        "input_file": args.input,
        "cluster_count": args.clusters,
        "feature_names": feature_names,
        "clusters": [],
    }

    for cluster_index in range(args.clusters):
        cluster_tracks = [track for track, label in zip(tracks, labels) if int(label) == cluster_index]
        centroid = centroids[cluster_index]
        cluster_payload["clusters"].append(
            {
                "cluster_id": cluster_index,
                "size": len(cluster_tracks),
                "top_axes": top_axes(centroid, feature_names),
                "tracks": [
                    {
                        "id": track["id"],
                        "title": track.get("title"),
                        "artists": track.get("artists", []),
                    }
                    for track in cluster_tracks
                ],
            }
        )

    Path(args.output).write_text(json.dumps(cluster_payload, ensure_ascii=False, indent=2))

    print(f"Input: {args.input}")
    print(f"Tracks clustered: {len(tracks)}")
    print(f"Clusters: {args.clusters}")
    print(f"Output: {args.output}")
    for cluster in cluster_payload["clusters"]:
        print(
            f"Cluster {cluster['cluster_id']}: size={cluster['size']} top_axes="
            + ", ".join(f"{axis['feature']}={axis['value']}" for axis in cluster["top_axes"])
        )


if __name__ == "__main__":
    main()