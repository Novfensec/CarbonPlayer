# VideoNative Player with CarbonKivy

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Framework](https://img.shields.io/badge/UI-CarbonKivy-FF7B00.svg?style=for-the-badge)](https://github.com/Novfensec)
[![Backend](https://img.shields.io/badge/Backend-videonative-85EA2D.svg?style=for-the-badge&logo=c%2B%2B&logoColor=white)](https://github.com/novfensec/videonative)
[![Platform Support](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20Android-purple.svg?style=for-the-badge)](https://github.com/Novfensec)

An ultra-responsive, threaded video player application built for both desktop and mobile devices. By combining the sleek design language of **CarbonKivy** with the high-performance decoding engine of **videonative** (a custom C++ module bridging FFmpeg and Pybind11), this player guarantees smooth, millisecond-accurate multimedia playback.


## Architectural Overview

The application is structured into three distinct layers to ensure optimal threading, zero UI lag, and smooth rendering:

1. **High-Performance C++ Core (`videonative`):**
   - Utilizes **FFmpeg** (`libavcodec`, `libavformat`, `libswscale`) to decode video frames and convert raw PTS (Presentation Time Stamp) ticks into fractional seconds.
   - Synchronizes audio directly with hardware clocks using raw audio samples (`miniaudio`), acting as the high-accuracy master clock for video frames.
   - Built with **Pybind11** and **scikit-build-core** to expose a native `.pyd` / `.so` module directly to Python.

2. **Python Widget Core (`PlayerBase`):**
   - Spawns background worker loops via standard Python threads (`threading.Thread`) to continuously pull NumPy array data from the C++ decoder.
   - Uses thread-safe queues to stage decodes while the UI thread handles drawing.
   - Leverages **Kivy's `Clock.schedule_interval`** and vertical texture flipping to efficiently blit raw bytes onto Kivy's graphics canvas.

3. **Android System Management (`android_utils.py`):**
   - Implements zero-padding, immersive sticky fullscreen mode, and sensor-based rotation using **Pyjnius**.
   - Integrates seamlessly with Kivy's mobile application lifecycle to properly pause and resume decoders on background/foreground transitions.


## 🛠️ Features

- **True Immersive Landscape Fullscreen:** Automatically rotates mobile screens to sensor landscape mode while rendering perfectly into camera cutouts and notches on Android 15 (SDK 35+).
- **Responsive System UI:** Detaches status bar and navigation bar insets listeners during playback to prevent overlapping UI glitches, reverting cleanly on exit.
- **Accurate Progress Control:** Implements timebase decoding that accurately reflects fractional seconds, supporting seeks and instant resets.
- **Dynamic Play/Pause & Audio Lifecycle:** Synchronously halts or resumes decoding threads, preventing memory leaks and background audio ghosting.


## 🚀 Installation & Setup

### Prerequisites

- Follow the instructions to install [videonative](https://github.com/novfensec/videonative) from its README file.

#### Windows
- **Visual Studio** with the "Desktop development with C++" workload.
- **FFmpeg 4.4+ / 5.x / 6.x Shared Build** installed.
- Ensure the FFmpeg `bin` folder containing the `.dll` files is added to your environment path, or specified directly in the python setup:
  ```python
  os.add_dll_directory("C:/Users/YourUser/Downloads/ffmpeg/bin")
  ```

#### Linux
- `pkg-config` and essential build tools (`build-essential`).
- FFmpeg development libraries:
  ```bash
  sudo apt-get install libavcodec-dev libavformat-dev libswscale-dev libswresample-dev libavutil-dev
  ```

### Building the Native Module

Either install directly from github:

- Windows powershell

    ```powershell
    $env:DEFAULT_FFMPEG_DIR="$env:USERPROFILE\Downloads\ffmpeg"; pip install https://github.com/novfensec/videonative/archive/main.zip
    ```

- Linux

    ```sh
    pip install https://github.com/novfensec/videonative/archive/main.zip
    ```

OR

Clone the repository and compile the native C++ Python module using `pip`:

```bash
git clone [https://github.com/Novfensec/videonative.git](https://github.com/Novfensec/videonative.git)
cd videonative

pip install -e .
```

---

## 📱 Android Build Details

To compile this player for Android, configure your `buildozer.spec` file with the following requirements:

```ini
# (buildozer.spec requirements)
requirements = python3, kivy==2.3.1, ffmpeg, android, pyjnius, https://github.com/carbonkivy/carbonkivy/archive/master.zip, numpy, videonative

android.api = 36
android.minapi = 24
android.ndk = 28c
android.ndk_api = 24

p4a.fork = novfensec
p4a.branch = videonative
```

## 📄 License

This project is open-source and available under the MIT License. See the [LICENSE](LICENSE) file for more information.

Author: **[Kartavya Shukla](https://github.com/Novfensec)**
