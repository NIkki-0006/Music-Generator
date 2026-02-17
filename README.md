


# 🎧 AI Music Remix & Mood Generator

An interactive **Streamlit-based AI Music Application** that allows users to:

* 🎼 Generate music tracks based on different moods
* 🔀 Remix existing WAV audio files
* 🎛 Control intensity and randomness
* 📥 Download generated audio instantly

This project demonstrates basic **audio signal processing, procedural music synthesis, and remix algorithms using Python**.

---

## 🚀 Features

### 🎼 Mood Generator

* Generate music based on moods:

  * Happy 😊
  * Sad 😢
  * Chill 🌿
  * Energetic ⚡
  * Dark 🌑
* Adjustable:

  * Duration (5–120 seconds)
  * Sample rate (22050–48000 Hz)
  * Random seed (optional, for reproducible results)
* Automatic WAV download option

### 🔀 Remix WAV

* Upload your own `.wav` file
* Adjust remix intensity (0.0 – 1.0)
* Optional seed for controlled randomness
* Download remixed output

---

## 🛠 Technologies Used

* **Python 3**
* **Streamlit** – UI Framework
* **Wave & Struct** – Audio file handling
* **Math & Random** – Sound synthesis
* **Temporary File Handling** – Safe processing

---

## 🧠 How It Works

### 🎵 Mood Track Generation

The system:

* Defines a **mood profile** (BPM, scale, chord progression)
* Generates:

  * Chord layers
  * Bass layers
  * Optional arpeggios
* Applies:

  * Envelope shaping
  * Low-pass filtering
  * Normalization
* Outputs a 16-bit PCM WAV file

### 🔀 Remix Engine

The remix algorithm:

* Splits audio into beat-sized chunks
* Randomly:

  * Shuffles chunks
  * Reverses sections
  * Adds stutter effects
  * Skips sections
* Applies crossfade between chunks
* Adds low-pass filtering
* Normalizes final output

---

## 📂 Project Structure

```
AI-Music-Remix/
│
├── app.py                 # Main Streamlit application
├── musicintro.py          # (Optional) External audio logic module
├── README.md
```

If `musicintro.py` is not found, the app automatically uses the built-in fallback implementation.

---

## ⚙️ Installation

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/ai-music-remix.git
cd ai-music-remix
```

### 2️⃣ Install dependencies

```bash
pip install streamlit
```

(Other libraries used are built-in Python modules.)

---

## ▶️ Running the Application

```bash
streamlit run app.py
```

The app will open in your browser.

---

## 🎚 Parameters Explanation

| Parameter       | Description                           |
| --------------- | ------------------------------------- |
| Mood            | Defines BPM, scale, chord progression |
| Duration        | Length of generated track             |
| Sample Rate     | Audio quality                         |
| Seed            | Controls randomness                   |
| Remix Intensity | Controls amount of transformation     |

---

## 📌 Use Cases

* 🎓 Student AI Project
* 🎶 Music Experimentation
* 🎛 Beginner DSP Learning
* 🤖 Generative AI Demonstration
* 🧪 Audio Algorithm Research

---


