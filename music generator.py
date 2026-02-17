import math
import random
import struct
import sys
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st


PROJECT_DIR = Path(__file__).resolve().parent
if str(PROJECT_DIR) not in sys.path:
	sys.path.insert(0, str(PROJECT_DIR))

try:
	from musicintro import (  # type: ignore[reportMissingImports]
		generate_mood_track,
		load_wav_mono,
		mood_profile,
		remix_track,
		save_wav_mono,
	)
except ModuleNotFoundError:
	def clamp16(value: float) -> int:
		return max(-32768, min(32767, int(value)))


	def load_wav_mono(path: str) -> Tuple[int, List[int]]:
		with wave.open(path, "rb") as wav_file:
			channels = wav_file.getnchannels()
			sample_width = wav_file.getsampwidth()
			sample_rate = wav_file.getframerate()
			frames = wav_file.readframes(wav_file.getnframes())

		if sample_width not in (1, 2):
			raise ValueError("Only 8-bit or 16-bit PCM WAV files are supported.")

		if sample_width == 1:
			raw = list(frames)
			samples = [value - 128 for value in raw]
		else:
			total = len(frames) // 2
			samples = list(struct.unpack("<" + "h" * total, frames))

		if channels > 1:
			mono = []
			for index in range(0, len(samples), channels):
				mono.append(int(sum(samples[index:index + channels]) / channels))
			samples = mono

		if sample_width == 1:
			samples = [value * 256 for value in samples]

		return sample_rate, samples


	def save_wav_mono(path: str, sample_rate: int, samples: List[int]) -> None:
		pcm = struct.pack("<" + "h" * len(samples), *[clamp16(sample) for sample in samples])
		with wave.open(path, "wb") as wav_file:
			wav_file.setnchannels(1)
			wav_file.setsampwidth(2)
			wav_file.setframerate(sample_rate)
			wav_file.writeframes(pcm)


	def normalize(samples: List[int], target_peak: int = 29000) -> List[int]:
		if not samples:
			return samples
		peak = max(abs(sample) for sample in samples)
		if peak == 0:
			return samples
		gain = target_peak / peak
		return [clamp16(sample * gain) for sample in samples]


	def crossfade_append(base: List[int], chunk: List[int], fade_samples: int) -> List[int]:
		if not base:
			return chunk[:]
		fade_samples = min(fade_samples, len(base), len(chunk))
		if fade_samples <= 0:
			return base + chunk

		start = len(base) - fade_samples
		output = base[:start]
		for index in range(fade_samples):
			mix_a = (fade_samples - index) / fade_samples
			mix_b = index / fade_samples
			value = base[start + index] * mix_a + chunk[index] * mix_b
			output.append(clamp16(value))
		output.extend(chunk[fade_samples:])
		return output


	def apply_lowpass(samples: List[int], window: int) -> List[int]:
		if window <= 1 or not samples:
			return samples
		output: List[int] = []
		running_sum = 0
		buffer: List[int] = []
		for sample in samples:
			running_sum += sample
			buffer.append(sample)
			if len(buffer) > window:
				running_sum -= buffer.pop(0)
			output.append(clamp16(running_sum / len(buffer)))
		return output


	def remix_track(samples: List[int], sample_rate: int, intensity: float, seed: int | None) -> List[int]:
		rng = random.Random(seed)
		beat_samples = int(sample_rate * 0.5)
		beat_samples = max(2048, beat_samples)
		chunks = [samples[index:index + beat_samples] for index in range(0, len(samples), beat_samples)]

		if len(chunks) < 2:
			return samples

		shuffled = chunks[:]
		rng.shuffle(shuffled)

		remixed: List[int] = []
		reverse_probability = min(0.5, 0.1 + intensity * 0.35)
		stutter_probability = min(0.6, 0.1 + intensity * 0.4)
		skip_probability = min(0.35, intensity * 0.2)

		for chunk in shuffled:
			working = chunk[:]
			if rng.random() < skip_probability:
				continue
			if rng.random() < reverse_probability:
				working.reverse()
			if rng.random() < stutter_probability and len(working) > 64:
				section = working[: len(working) // 4]
				repeats = rng.randint(2, 4)
				working = section * repeats + working

			gain = 0.8 + rng.random() * (0.4 + intensity * 0.3)
			working = [clamp16(sample * gain) for sample in working]
			remixed = crossfade_append(remixed, working, fade_samples=int(sample_rate * 0.01))

		remixed = apply_lowpass(remixed, window=max(2, int(8 - intensity * 4)))
		return normalize(remixed)


	def midi_to_freq(note: int) -> float:
		return 440.0 * (2 ** ((note - 69) / 12))


	def synth_tone(freq: float, duration: float, sample_rate: int, volume: float, rng: random.Random) -> List[float]:
		total = max(1, int(duration * sample_rate))
		attack = max(1, int(total * 0.03))
		release = max(1, int(total * 0.15))
		sustain_start = attack
		sustain_end = max(sustain_start + 1, total - release)
		output: List[float] = []

		phase_offset = rng.random() * math.pi
		for index in range(total):
			t = index / sample_rate
			base = math.sin(2 * math.pi * freq * t + phase_offset)
			harmonic = 0.35 * math.sin(2 * math.pi * freq * 2 * t)
			overtone = 0.12 * math.sin(2 * math.pi * freq * 3 * t)
			wave_value = (base + harmonic + overtone) * volume

			if index < attack:
				env = index / attack
			elif index > sustain_end:
				env = max(0.0, (total - index) / release)
			else:
				env = 0.85
			output.append(wave_value * env)
		return output


	def add_to_mix(track: List[float], sound: List[float], start: int) -> None:
		end = min(len(track), start + len(sound))
		for index in range(start, end):
			track[index] += sound[index - start]


	def mood_profile(mood: str) -> Dict[str, object]:
		profiles: Dict[str, Dict[str, object]] = {
			"happy": {"bpm": 118, "root": 60, "scale": [0, 2, 4, 5, 7, 9, 11], "prog": [0, 4, 5, 3]},
			"sad": {"bpm": 84, "root": 57, "scale": [0, 2, 3, 5, 7, 8, 10], "prog": [0, 5, 3, 4]},
			"chill": {"bpm": 92, "root": 62, "scale": [0, 2, 3, 5, 7, 9, 10], "prog": [0, 3, 4, 3]},
			"energetic": {"bpm": 132, "root": 64, "scale": [0, 2, 4, 5, 7, 9, 11], "prog": [0, 5, 4, 5]},
			"dark": {"bpm": 78, "root": 50, "scale": [0, 1, 3, 5, 7, 8, 10], "prog": [0, 6, 5, 4]},
		}
		if mood not in profiles:
			raise ValueError(f"Unsupported mood: {mood}. Choose from: {', '.join(profiles)}")
		return profiles[mood]


	def generate_mood_track(mood: str, duration: float, sample_rate: int, seed: int | None) -> List[int]:
		rng = random.Random(seed)
		profile = mood_profile(mood)
		bpm = int(profile["bpm"])
		root = int(profile["root"])
		scale = profile["scale"]
		progression = profile["prog"]

		beat_length = 60.0 / bpm
		total_samples = int(duration * sample_rate)
		track = [0.0] * total_samples

		chords: List[List[int]] = []
		for degree in progression:
			chord_root = root + scale[degree % len(scale)]
			chord = [chord_root, chord_root + 3 + (degree % 2), chord_root + 7]
			chords.append(chord)

		beat_index = 0
		while int(beat_index * beat_length * sample_rate) < total_samples:
			chord = chords[beat_index % len(chords)]
			start_sample = int(beat_index * beat_length * sample_rate)

			for note in chord:
				freq = midi_to_freq(note)
				tone = synth_tone(freq, duration=beat_length * 1.9, sample_rate=sample_rate, volume=0.12, rng=rng)
				add_to_mix(track, tone, start_sample)

			bass_note = chord[0] - 12
			bass = synth_tone(midi_to_freq(bass_note), duration=beat_length * 0.95, sample_rate=sample_rate, volume=0.2, rng=rng)
			add_to_mix(track, bass, start_sample)

			if mood in ("energetic", "happy") and beat_index % 2 == 0:
				arp_note = chord[rng.randint(0, 2)] + 12
				arp = synth_tone(midi_to_freq(arp_note), duration=beat_length * 0.4, sample_rate=sample_rate, volume=0.09, rng=rng)
				add_to_mix(track, arp, start_sample + int(beat_length * 0.5 * sample_rate))

			beat_index += 1

		rendered = [clamp16(sample * 26000) for sample in track]
		filtered = apply_lowpass(rendered, window=4 if mood in ("chill", "sad", "dark") else 2)
		return normalize(filtered, target_peak=28000)


MOOD_ACCENTS = {
	"happy": "#F97316",
	"sad": "#3B82F6",
	"chill": "#14B8A6",
	"energetic": "#EF4444",
	"dark": "#8B5CF6",
}


def save_to_bytes(sample_rate: int, samples: list[int]) -> bytes:
	pcm_path = None
	with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_out:
		pcm_path = temp_out.name
	try:
		save_wav_mono(pcm_path, sample_rate, samples)
		return Path(pcm_path).read_bytes()
	finally:
		if pcm_path and Path(pcm_path).exists():
			Path(pcm_path).unlink()


def render_header() -> None:
	st.markdown(
		"""
		<style>
		.main {
			background: #ffffff;
		}
		.block-container {
			padding-top: 1.2rem;
			padding-bottom: 2rem;
		}
		.title-card {
			background: linear-gradient(90deg, #0ea5e9, #22c55e);
			padding: 16px 20px;
			border-radius: 14px;
			margin-bottom: 14px;
			color: white;
		}
		.panel-card {
			background: #f8fafc;
			padding: 14px;
			border: 1px solid #e2e8f0;
			border-radius: 12px;
		}
		</style>
		<div class="title-card">
			<h2 style="margin:0;">🎧 AI Music Remix & Mood Generator</h2>
			<p style="margin:6px 0 0 0;">Create mood tracks or remix WAV files in a few clicks.</p>
		</div>
		""",
		unsafe_allow_html=True,
	)


def mood_generator_tab() -> None:
	st.markdown('<div class="panel-card">', unsafe_allow_html=True)
	mood = st.selectbox("Mood", ["happy", "sad", "chill", "energetic", "dark"], index=2)
	duration = st.slider("Duration (seconds)", min_value=5, max_value=120, value=20, step=1)
	sample_rate = st.select_slider("Sample rate", options=[22050, 32000, 44100, 48000], value=44100)
	seed_text = st.text_input("Seed (optional)", value="", placeholder="e.g. 42")
	st.markdown("</div>", unsafe_allow_html=True)

	profile = mood_profile(mood)
	accent = MOOD_ACCENTS[mood]
	st.markdown(
		f"<p style='margin-top:8px;'>Mood BPM: <span style='color:{accent}; font-weight:700;'>{profile['bpm']}</span></p>",
		unsafe_allow_html=True,
	)

	if st.button("Generate Track", type="primary", use_container_width=True):
		with st.spinner("Creating your mood track..."):
			seed = int(seed_text) if seed_text.strip().isdigit() else None
			samples = generate_mood_track(
				mood=mood,
				duration=float(duration),
				sample_rate=int(sample_rate),
				seed=seed,
			)
			wav_bytes = save_to_bytes(int(sample_rate), samples)

		st.success("Mood track generated.")
		st.audio(wav_bytes, format="audio/wav")
		st.download_button(
			"Download WAV",
			data=wav_bytes,
			file_name=f"{mood}_track.wav",
			mime="audio/wav",
			use_container_width=True,
		)


def remix_tab() -> None:
	st.markdown('<div class="panel-card">', unsafe_allow_html=True)
	uploaded = st.file_uploader("Upload WAV file", type=["wav"])
	intensity = st.slider("Remix intensity", min_value=0.0, max_value=1.0, value=0.6, step=0.05)
	seed_text = st.text_input("Seed (optional)", key="remix_seed", value="", placeholder="e.g. 99")
	st.markdown("</div>", unsafe_allow_html=True)

	if uploaded is not None:
		st.audio(uploaded.getvalue(), format="audio/wav")

	if st.button("Create Remix", use_container_width=True):
		if uploaded is None:
			st.warning("Please upload a WAV file first.")
			return

		with st.spinner("Remixing audio..."):
			seed = int(seed_text) if seed_text.strip().isdigit() else None
			input_path = None
			output_path = None
			try:
				with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_in:
					input_path = temp_in.name
					temp_in.write(uploaded.getvalue())

				sample_rate, samples = load_wav_mono(input_path)
				remixed = remix_track(samples, sample_rate=sample_rate, intensity=float(intensity), seed=seed)

				with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_out:
					output_path = temp_out.name
				save_wav_mono(output_path, sample_rate, remixed)
				remix_bytes = Path(output_path).read_bytes()
			finally:
				if input_path and Path(input_path).exists():
					Path(input_path).unlink()
				if output_path and Path(output_path).exists():
					Path(output_path).unlink()

		st.success("Remix created.")
		st.audio(remix_bytes, format="audio/wav")
		st.download_button(
			"Download Remix",
			data=remix_bytes,
			file_name="remix_output.wav",
			mime="audio/wav",
			use_container_width=True,
		)


def main() -> None:
	st.set_page_config(page_title="AI Music Remix & Mood Generator", page_icon="🎵", layout="centered")
	render_header()
	tab_generate, tab_remix = st.tabs(["🎼 Mood Generator", "🔀 Remix WAV"])

	with tab_generate:
		mood_generator_tab()
	with tab_remix:
		remix_tab()


if __name__ == "__main__":
	try:
		from streamlit.runtime.scriptrunner import get_script_run_ctx
		is_streamlit_context = get_script_run_ctx() is not None
	except Exception:
		is_streamlit_context = False

	if is_streamlit_context:
		main()
	else:
		from streamlit.web import cli as stcli
		sys.argv = ["streamlit", "run", __file__]
		raise SystemExit(stcli.main())
