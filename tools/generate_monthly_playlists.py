#!/usr/bin/env python3
"""Generate monthly playlists from clusters with capped sizes and randomized fallback tracks."""

import argparse
import json
import random
from datetime import datetime
from pathlib import Path


SCENE_PROFILES = [
    {
        "theme": "nocturne_urbain",
        "cluster_axis_preferences": ["spectral_centroid_hz", "onset_rate_per_sec", "rms_std"],
        "track_score_features": ["brightness", "energy", "onset_rate_per_sec", "mood_party_probability"],
        "phrases": [
            "Neons sous pluie",
            "Sortie apres minuit",
            "Dernier metro plein",
            "Phares sur le periph",
            "Bitume encore chaud",
            "Vitrine a deux heures",
            "Taxi dans le noir",
            "Retour avant l aube",
            "Terrasse en veille",
            "Couloir du matin",
        ],
    },
    {
        "theme": "crepuscule_souple",
        "cluster_axis_preferences": ["bass_ratio", "crest_factor", "zero_crossing_rate"],
        "track_score_features": ["bass", "danceability_probability", "bass_ratio", "silence_ratio"],
        "phrases": [
            "Le jour retombe",
            "Le soleil baisse",
            "Balcon en or",
            "Rue encore tiede",
            "La ville ralentit",
            "Fin de terrasse",
            "L ombre s allonge",
            "Derniere lumiere",
            "Retour sans bruit",
            "Avant le diner",
        ],
    },
    {
        "theme": "air_ouvert",
        "cluster_axis_preferences": ["silence_ratio", "loudness_dbfs", "crest_factor"],
        "track_score_features": ["silence_ratio", "crest_factor", "mood_relaxed_probability", "loudness_dbfs"],
        "phrases": [
            "Fenetre ouverte",
            "Rideaux qui bougent",
            "Vent dans la chambre",
            "Cafe sur le toit",
            "Matin sans message",
            "Plantes au balcon",
            "Volets a demi clos",
            "Silence dans l air",
            "Linge au soleil",
            "Parfum de dehors",
        ],
    },
    {
        "theme": "nuit_tendue",
        "cluster_axis_preferences": ["zero_crossing_rate", "spectral_flatness", "spectral_centroid_hz"],
        "track_score_features": ["spectral_flatness", "zero_crossing_rate", "mood_sad_probability", "vocal"],
        "phrases": [
            "Personne ne dort",
            "Cafe encore ouvert",
            "Fumee sur le quai",
            "L appel du soir",
            "Escalier desert",
            "Ville apres une heure",
            "Pluie contre vitre",
            "L ombre du bus",
            "Lampe dans la cour",
            "Soleil deja loin",
        ],
    },
    {
        "theme": "route_claire",
        "cluster_axis_preferences": ["loudness_dbfs", "rms_std", "spectral_centroid_hz"],
        "track_score_features": ["energy", "vocal", "mood_happy_probability", "loudness_dbfs"],
        "phrases": [
            "On reprend la route",
            "Vitres un peu basses",
            "Sortie de rocade",
            "Plein fait trop tard",
            "Feu vert au loin",
            "Pont avant l aube",
            "Bretelle vers l ouest",
            "Nuit sur l autoroute",
            "Halte sur le bord",
            "Parking encore vide",
        ],
    },
    {
        "theme": "coeur_de_foule",
        "cluster_axis_preferences": ["onset_rate_per_sec", "zero_crossing_rate", "loudness_dbfs"],
        "track_score_features": ["energy", "intensity", "tempo_bpm", "mood_party_probability"],
        "phrases": [
            "Dans la foule",
            "Au milieu du bruit",
            "Bras leves tard",
            "Devant la scene",
            "Queue sous les neons",
            "Sortie de concert",
            "Bruit dans le hall",
            "Verres sur le zinc",
            "Porte qui bat",
            "Lumiere sur la file",
        ],
    },
    {
        "theme": "apres_averse",
        "cluster_axis_preferences": ["silence_ratio", "rms_std", "spectral_centroid_hz"],
        "track_score_features": ["dynamic", "mood_relaxed_probability", "mood_sad_probability", "brightness"],
        "phrases": [
            "Apres la pluie",
            "Pavés qui brillent",
            "Air froid soudain",
            "Capuche sur la tete",
            "Banc encore mouille",
            "Nuage qui s ouvre",
            "Rue lavee d un coup",
            "Flaques sous lampadaire",
            "Calme apres l orage",
            "Parapluie referme",
        ],
    },
    {
        "theme": "trajet_seul",
        "cluster_axis_preferences": ["bass_ratio", "spectral_centroid_hz", "crest_factor"],
        "track_score_features": ["bass", "dynamic_range", "vocal", "mood_happy_probability"],
        "phrases": [
            "La route est vide",
            "Feux rouges loin devant",
            "Virage sans personne",
            "Station presque fermee",
            "Sortie ratee exprès",
            "Pont sans trafic",
            "Rond point desert",
            "Banquette arriere vide",
            "Demie heure de marge",
            "Essuie glaces lents",
        ],
    },
]

FALLBACK_PROFILE = {
    "theme": "hors_cluster",
    "track_score_features": ["mood_relaxed_probability", "danceability_probability", "energy", "vocal"],
    "phrases": [
        "Sans se presser",
        "Entre deux gares",
        "Au bout du quai",
        "Quelques pas dehors",
        "Encore un detour",
        "Le temps de rentrer",
        "On laisse filer",
        "Pas de plan fixe",
        "Dans le train retour",
        "On verra demain",
    ],
}


def month_seed(month_key):
    return sum(ord(char) for char in month_key)


def combined_track_features(track):
    combined = {}
    for key in [
        "raw_features",
        "extended_preview_features",
        "extended_acousticbrainz_features",
        "preview_features",
        "acousticbrainz",
    ]:
        value = track.get(key)
        if isinstance(value, dict):
            combined.update(value)
    return combined


def track_score(track, feature_names):
    combined = combined_track_features(track)

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


def build_track_lookup(vector_payload, dataset_payload):
    track_lookup = {
        track["id"]: {
            "id": track["id"],
            "title": track.get("title"),
            "artists": track.get("artists", []),
            "preview_features": track.get("preview_features", {}),
            "acousticbrainz": track.get("acousticbrainz", {}),
        }
        for track in dataset_payload
    }

    for track in vector_payload["tracks"]:
        existing = track_lookup.setdefault(
            track["id"],
            {"id": track["id"], "title": track.get("title"), "artists": track.get("artists", [])},
        )
        existing.update(track)

    return track_lookup


def assign_profiles_to_clusters(clusters):
    remaining_clusters = [cluster for cluster in clusters if cluster.get("tracks")]
    assignments = []

    for profile in SCENE_PROFILES:
        if not remaining_clusters:
            break
        ranked_clusters = sorted(
            remaining_clusters,
            key=lambda cluster: cluster_fit(cluster, profile["cluster_axis_preferences"]),
            reverse=True,
        )
        selected_cluster = ranked_clusters[0]
        assignments.append((selected_cluster, profile))
        remaining_clusters = [cluster for cluster in remaining_clusters if cluster["cluster_id"] != selected_cluster["cluster_id"]]

    for cluster in remaining_clusters:
        assignments.append((cluster, SCENE_PROFILES[len(assignments) % len(SCENE_PROFILES)]))

    return assignments


def choose_phrase(profile, used_phrases, cluster_id, chunk_index):
    phrases = profile["phrases"]
    start_index = (cluster_id * 3 + chunk_index) % len(phrases) if cluster_id is not None else chunk_index % len(phrases)

    for offset in range(len(phrases)):
        candidate = phrases[(start_index + offset) % len(phrases)]
        if candidate not in used_phrases:
            used_phrases.add(candidate)
            return candidate

    candidate = f"{phrases[start_index]} {chunk_index + 1}"
    used_phrases.add(candidate)
    return candidate


def build_playlist_name(index, phrase):
    return f"{index:02d} - {phrase}"


def build_playlist_track(score, track, source):
    return {
        "id": track["id"],
        "title": track.get("title"),
        "artists": track.get("artists", []),
        "score": round(score, 4),
        "source": source,
    }


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
    parser.add_argument("--dataset", default="final_dataset.json", help="Dataset JSON file")
    parser.add_argument("--vectors", default="clustering_vectors.json", help="Vector JSON file")
    parser.add_argument("--clusters", default="clusters.json", help="Cluster JSON file")
    parser.add_argument("--output", default="monthly_playlists.json", help="Output playlist JSON file")
    parser.add_argument("--month", default=datetime.now().strftime("%Y-%m"), help="Month key, e.g. 2026-04")
    parser.add_argument("--playlist-size", type=int, default=50, help="Maximum tracks per generated playlist")
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

    dataset_payload = json.loads(Path(args.dataset).read_text())
    vector_payload = json.loads(Path(args.vectors).read_text())
    cluster_payload = json.loads(Path(args.clusters).read_text())
    history_path = args.history or f"{Path(args.output).stem}_history.json"
    history_payload = load_history(history_path)
    recent_ids = recent_track_ids(history_payload, args.lookback_months)

    rng = random.Random(month_seed(args.month))
    track_lookup = build_track_lookup(vector_payload, dataset_payload)
    used_phrases = set()
    clustered_track_ids = set()
    playlists = []
    playlist_index = 1

    assignments = sorted(assign_profiles_to_clusters(cluster_payload["clusters"]), key=lambda item: item[0].get("size", 0), reverse=True)
    for selected_cluster, profile in assignments:
        candidates = []
        for track_stub in selected_cluster.get("tracks", []):
            track = track_lookup.get(track_stub["id"])
            if not track:
                continue
            score = track_score(track, profile["track_score_features"])
            if track["id"] in recent_ids:
                score -= args.repeat_penalty
            jitter = rng.random() * 0.05
            candidates.append((score + jitter, track, selected_cluster, profile))
            clustered_track_ids.add(track["id"])

        candidates.sort(key=lambda item: item[0], reverse=True)
        for chunk_index, start in enumerate(range(0, len(candidates), args.playlist_size)):
            chunk = candidates[start : start + args.playlist_size]
            phrase = choose_phrase(profile, used_phrases, selected_cluster["cluster_id"], chunk_index)
            playlists.append(
                {
                    "month": args.month,
                    "profile": build_playlist_name(playlist_index, phrase),
                    "scene_theme": profile["theme"],
                    "source_cluster": selected_cluster["cluster_id"],
                    "source_clusters": [selected_cluster["cluster_id"]],
                    "cluster_top_axes": selected_cluster.get("top_axes", []),
                    "track_score_features": list(profile["track_score_features"]),
                    "tracks": [build_playlist_track(score, track, "cluster") for score, track, _, _ in chunk],
                }
            )
            playlist_index += 1

    non_clustered_tracks = [
        track_lookup[track["id"]]
        for track in dataset_payload
        if track["id"] in track_lookup and track["id"] not in clustered_track_ids
    ]
    rng.shuffle(non_clustered_tracks)

    available_slots = []
    for playlist_idx, playlist in enumerate(playlists):
        available_slots.extend([playlist_idx] * (args.playlist_size - len(playlist["tracks"])))
    rng.shuffle(available_slots)

    assigned_non_clustered = 0
    for playlist_idx, track in zip(available_slots, non_clustered_tracks):
        playlists[playlist_idx]["tracks"].append(build_playlist_track(0.0, track, "random_no_features"))
        assigned_non_clustered += 1

    remaining_tracks = non_clustered_tracks[assigned_non_clustered:]
    fallback_candidates = []
    for track in remaining_tracks:
        score = track_score(track, FALLBACK_PROFILE["track_score_features"])
        if track["id"] in recent_ids:
            score -= args.repeat_penalty
        jitter = rng.random() * 0.05
        fallback_candidates.append((score + jitter, track))

    fallback_candidates.sort(key=lambda item: item[0], reverse=True)
    for chunk_index, start in enumerate(range(0, len(fallback_candidates), args.playlist_size)):
        chunk = fallback_candidates[start : start + args.playlist_size]
        phrase = choose_phrase(FALLBACK_PROFILE, used_phrases, None, chunk_index)
        playlists.append(
            {
                "month": args.month,
                "profile": build_playlist_name(playlist_index, phrase),
                "scene_theme": FALLBACK_PROFILE["theme"],
                "source_cluster": None,
                "source_clusters": [],
                "cluster_top_axes": [],
                "track_score_features": list(FALLBACK_PROFILE["track_score_features"]),
                "tracks": [build_playlist_track(score, track, "random_no_features") for score, track in chunk],
            }
        )
        playlist_index += 1

    output_payload = {
        "month": args.month,
        "cluster_count": cluster_payload.get("cluster_count"),
        "clustered_track_count": len(clustered_track_ids),
        "non_clustered_track_count": len(non_clustered_tracks),
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
    print(f"Clusters used: {cluster_payload.get('cluster_count')}")
    print(f"Playlists generated: {len(playlists)}")
    print(f"Output: {args.output}")
    print(f"History: {history_path}")
    print(f"Tracks assigned: {sum(len(playlist['tracks']) for playlist in playlists)}")
    print(f"Non-clustered tracks assigned randomly: {len(non_clustered_tracks)}")
    for playlist in playlists:
        print(f"{playlist['profile']}: cluster={playlist['source_cluster']} tracks={len(playlist['tracks'])}")


if __name__ == "__main__":
    main()