"""Shared audio feature extraction for Deezer previews."""

from pydub import AudioSegment
import numpy as np


def analyze_audio(audio_path):
    """Extract practical audio features from a preview MP3."""
    try:
        audio = AudioSegment.from_mp3(str(audio_path))

        duration = len(audio) / 1000.0
        dbfs = audio.dBFS
        sample_rate = audio.frame_rate

        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        if audio.channels == 2:
            samples = samples.reshape((-1, 2)).mean(axis=1)

        if audio.sample_width == 2:
            samples = samples / (2**15)
        elif audio.sample_width == 1:
            samples = samples / (2**7)

        fft = np.fft.rfft(samples)
        freqs = np.fft.rfftfreq(len(samples), 1 / sample_rate)
        magnitude = np.abs(fft)

        bass_band = magnitude[(freqs >= 20) & (freqs < 250)].sum()
        mid_band = magnitude[(freqs >= 250) & (freqs < 2000)].sum()
        high_band = magnitude[(freqs >= 2000) & (freqs < 8000)].sum()
        total_mag = bass_band + mid_band + high_band + 1e-10

        sample_chunk = min(len(samples), int(sample_rate * 5))
        samples_chunk = samples[:sample_chunk]

        autocorr = np.correlate(samples_chunk, samples_chunk, mode="full")
        autocorr = autocorr[len(autocorr) // 2 :]

        min_period = int(sample_rate * 60 / 180)
        max_period = int(sample_rate * 60 / 60)

        if max_period < len(autocorr):
            peak_idx = np.argmax(autocorr[min_period:max_period]) + min_period
            tempo_bpm = 60 * sample_rate / peak_idx
        else:
            tempo_bpm = 120.0

        window_size = 2048
        hop_size = 1024
        if len(samples) < window_size:
            frames = samples.reshape(1, -1)
        else:
            frames = np.array(
                [samples[i:i + window_size] for i in range(0, len(samples) - window_size + 1, hop_size)],
                dtype=np.float32,
            )

        rms_frames = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
        rms_mean = float(np.mean(rms_frames))
        rms_std = float(np.std(rms_frames))

        zcr_frames = np.mean(np.abs(np.diff(np.signbit(frames), axis=1)), axis=1)
        zcr_mean = float(np.mean(zcr_frames))

        total_spectrum = float(np.sum(magnitude) + 1e-12)
        spectral_centroid = float(np.sum(freqs * magnitude) / total_spectrum)

        cumulative = np.cumsum(magnitude)
        rolloff_threshold = 0.85 * total_spectrum
        rolloff_idx = int(np.searchsorted(cumulative, rolloff_threshold))
        rolloff_idx = min(rolloff_idx, len(freqs) - 1)
        spectral_rolloff = float(freqs[rolloff_idx])

        geometric_mean = float(np.exp(np.mean(np.log(magnitude + 1e-12))))
        arithmetic_mean = float(np.mean(magnitude) + 1e-12)
        spectral_flatness = geometric_mean / arithmetic_mean

        silence_ratio = float(np.mean(np.abs(samples) < 0.01))

        peak_amp = np.max(np.abs(samples))
        dynamic_range = np.max(samples) - np.min(samples)
        crest_factor = float(peak_amp / (rms_mean + 1e-12))

        energy_diff = np.diff(rms_frames)
        onset_threshold = float(np.std(energy_diff))
        onset_events = int(np.sum(energy_diff > onset_threshold))
        onset_rate = float(onset_events / max(duration, 1e-6))

        bass_ratio = float(bass_band / total_mag)
        mid_ratio = float(mid_band / total_mag)
        high_ratio = float(high_band / total_mag)

        tempo_score = min(100, max(0, (tempo_bpm - 60) / 1.2))
        energy_score = min(100, max(0, (dbfs + 40) * 2.857))
        bass_score = min(100, (bass_band / total_mag) * 200)
        brightness_score = min(100, (high_band / total_mag) * 150)
        vocal_score = min(100, (mid_band / total_mag) * 150)
        dynamic_score = min(100, max(0, (dynamic_range - 0.5) / 0.015))
        intensity_score = min(100, peak_amp * 100)
        variance = np.var(samples)
        complexity_score = min(100, variance * 5000)

        return {
            "duration_seconds": float(duration),
            "tempo": int(round(tempo_score)),
            "energy": int(round(energy_score)),
            "bass": int(round(bass_score)),
            "brightness": int(round(brightness_score)),
            "vocal": int(round(vocal_score)),
            "dynamic": int(round(dynamic_score)),
            "intensity": int(round(intensity_score)),
            "complexity": int(round(complexity_score)),
            "rms_energy": float(audio.rms),
            "rms_std": round(rms_std, 6),
            "zero_crossing_rate": round(zcr_mean, 6),
            "tempo_bpm": round(tempo_bpm, 1),
            "loudness_dbfs": round(dbfs, 2),
            "dynamic_range": round(float(dynamic_range), 6),
            "peak_amplitude": round(float(peak_amp), 6),
            "crest_factor": round(crest_factor, 4),
            "silence_ratio": round(silence_ratio, 4),
            "onset_rate_per_sec": round(onset_rate, 4),
            "spectral_centroid_hz": round(spectral_centroid, 1),
            "spectral_rolloff_85_hz": round(spectral_rolloff, 1),
            "spectral_flatness": round(float(spectral_flatness), 6),
            "bass_ratio": round(bass_ratio, 6),
            "mid_ratio": round(mid_ratio, 6),
            "high_ratio": round(high_ratio, 6),
        }
    except Exception:
        return None