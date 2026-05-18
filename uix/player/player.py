from __future__ import annotations

__all__ = (
    "PlayerBase",
    "PlayerControls",
    "Player",
    "PlayerLayout",
    "PlayerLoadingLayout",
)

import time
import queue
import videonative
import threading

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import RenderContext, BindTexture, Rectangle, Color
from kivy.graphics.texture import Texture
from kivy.uix.widget import Widget
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import (
    BooleanProperty,
    ObjectProperty,
    StringProperty,
    NumericProperty,
    ColorProperty,
)

from carbonkivy.behaviors import HoverBehavior
from carbonkivy.uix.boxlayout import CBoxLayout
from carbonkivy.uix.relativelayout import CRelativeLayout
from carbonkivy.uix.shell import UIShellButton
from carbonkivy.uix.loading import CLoadingLayout
from carbonkivy.utils import DEVICE_TYPE

from android_utils import maximize_video, minimize_video

NV12_SHADER = """$HEADER$
uniform sampler2D tex_uv;
uniform vec4 bg_color;
uniform float video_ready;

void main(void) {
    if (video_ready < 0.5) {
        gl_FragColor = frag_color * bg_color;
    } else {
        float y = texture2D(texture0, tex_coord0).r;
        float u = texture2D(tex_uv, tex_coord0).r - 0.5;
        float v = texture2D(tex_uv, tex_coord0).a - 0.5;
        
        float r = y + 1.402 * v;
        float g = y - 0.344136 * u - 0.714136 * v;
        float b = y + 1.772 * u;
        
        gl_FragColor = frag_color * vec4(r, g, b, 1.0);
    }
}
"""


class PlayerLoadingLayout(CLoadingLayout):
    loading = BooleanProperty(False)


class PlayerBase(Widget):

    filename = StringProperty()

    initial_color = ColorProperty([0.1, 0.1, 0.1, 1.0])

    _running = BooleanProperty(False)

    was_running = BooleanProperty(False)

    _paused = BooleanProperty(False)

    current_pos = NumericProperty()

    duration = NumericProperty()

    current_pos_ratio = NumericProperty()

    buffering = BooleanProperty(False)

    loader = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fps = 30.0
        self.frame_queue = queue.Queue(maxsize=3)
        self.read_thread = None
        self.decoder = None
        self._seeking = False

        self.tex_y = None
        self.tex_uv = None

        self.width_px = 0
        self.height_px = 0

        self.canvas = RenderContext(
            use_parent_modelview=True, use_parent_projection=True
        )
        self.canvas.shader.fs = NV12_SHADER

        with self.canvas:
            Color(1, 1, 1, 1)
            self.bind_uv = BindTexture(index=1)
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.canvas["tex_uv"] = 1
        self.canvas["video_ready"] = 0.0
        self.canvas["bg_color"] = list(self.initial_color)

        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def on_initial_color(self, instance, value):
        """Monitors changes to initial_color and dynamically updates the shader uniform."""
        if self.canvas:
            self.canvas["bg_color"] = value

    def on_filename(self, *args) -> None:
        if self.filename:
            self.open_video()

    def open_video(self, *args) -> None:
        threading.Thread(target=self._background_load, daemon=True).start()

    def _background_load(self):
        """THIS RUNS IN THE BACKGROUND: Heavy network & FFmpeg initialization."""
        try:
            temp_decoder = videonative.MediaDecoder(self.filename)
            gpu_active = temp_decoder.enable_gpu()
            print(
                f"Hardware Acceleration Status: {'Enabled' if gpu_active else 'Disabled (Software Fallback)'}"
            )

            temp_decoder.start()
            first_frame_data = temp_decoder.get_next_frame()

            if first_frame_data is None:
                raise RuntimeError("Failed to read the first frame of the video.")

            Clock.schedule_once(
                lambda dt: self._on_video_loaded(temp_decoder, first_frame_data), 0
            )
        except Exception as e:
            print(f"Video Load Error: {e}")

    def _on_video_loaded(self, loaded_decoder, first_frame_data) -> None:
        """THIS RUNS ON THE UI THREAD: Safely updates Kivy widgets."""
        self.decoder = loaded_decoder

        y_bytes, uv_bytes, self.width_px, self.height_px = first_frame_data

        self.tex_y = Texture.create(
            size=(self.width_px, self.height_px), colorfmt="luminance"
        )
        self.tex_y.flip_vertical()

        self.tex_uv = Texture.create(
            size=(self.width_px // 2, self.height_px // 2), colorfmt="luminance_alpha"
        )
        self.tex_uv.flip_vertical()

        self.tex_y.blit_buffer(y_bytes, colorfmt="luminance", bufferfmt="ubyte")
        self.tex_uv.blit_buffer(uv_bytes, colorfmt="luminance_alpha", bufferfmt="ubyte")

        self.rect.texture = self.tex_y
        self.bind_uv.texture = self.tex_uv

        self.canvas["video_ready"] = 1.0
        self.canvas.ask_update()
        self._update_rect()
        self.duration = self.decoder.get_duration()
        self.fps = self.decoder.get_fps()
        self.play()

    def _update_rect(self, *args):
        if not self.width_px or not self.height_px:
            self.rect.pos = self.pos
            self.rect.size = self.size
            return

        widget_w, widget_h = self.size

        if widget_h == 0 or widget_w == 0:
            return

        video_ratio = self.width_px / self.height_px
        widget_ratio = widget_w / widget_h

        if widget_ratio > video_ratio:
            fit_h = widget_h
            fit_w = fit_h * video_ratio
        else:
            fit_w = widget_w
            fit_h = fit_w / video_ratio

        pos_x = self.x + (widget_w - fit_w) / 2.0
        pos_y = self.y + (widget_h - fit_h) / 2.0

        self.rect.size = (fit_w, fit_h)
        self.rect.pos = (pos_x, pos_y)

    def _reader_loop(self):
        """THIS RUNS IN THE BACKGROUND: Reads frames and puts them in the queue."""
        while self._running and self.decoder:
            self.buffering = self.decoder.is_buffering()
            frame_data = self.decoder.get_next_frame()

            if frame_data is None:
                if self._running and not self._seeking:
                    try:
                        self.frame_queue.put(None, timeout=0.1)
                    except queue.Full:
                        pass
                break

            y_bytes, uv_bytes, _, _ = frame_data

            while self._running:
                try:
                    self.frame_queue.put((y_bytes, uv_bytes), timeout=0.1)
                    break
                except queue.Full:
                    continue

    def update_frame(self, dt) -> None:
        if self._seeking:
            return

        try:
            frame_data = self.frame_queue.get_nowait()

            if self.buffering:
                self.buffering = False

            if frame_data is None:
                self.current_pos = self.duration
                self.current_pos_ratio = 1.0
                self.pause()
                return

            y_bytes, uv_bytes = frame_data

            self.tex_y.blit_buffer(y_bytes, colorfmt="luminance", bufferfmt="ubyte")
            self.tex_uv.blit_buffer(
                uv_bytes, colorfmt="luminance_alpha", bufferfmt="ubyte"
            )

            self.canvas.ask_update()

            self.current_pos = self.decoder.get_position()
            self.current_pos_ratio = (
                self.current_pos / self.duration if self.duration > 0 else 0.0
            )

        except queue.Empty:
            if self.decoder:
                self.buffering = self.decoder.is_buffering()

    def play(self, *args) -> None:
        if self._running or self._seeking:
            return

        if self.duration > 0 and self.current_pos >= self.duration - 0.2:
            self.seek(-self.current_pos)
            return

        self._running = True
        self._paused = False

        if self.decoder:
            self.decoder.start()
            self.decoder.resume()

        self.read_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.read_thread.start()

        Clock.schedule_interval(self.update_frame, 1.0 / self.fps)

    def stop(self, *args) -> None:
        self._running = False
        self._paused = False
        Clock.unschedule(self.update_frame)

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        if self.decoder:
            self.decoder.stop()

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        self.read_thread = None

    def pause(self, *args) -> None:
        self._running = False
        self._paused = True

        if self.decoder:
            self.decoder.pause()

        Clock.unschedule(self.update_frame)

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=0.2)
            self.read_thread = None

    def seek(self, offset: float | int) -> None:
        if not self.decoder or self._seeking:
            return

        self._seeking = True
        was_running = self._running

        new_pos = max(0.0, min(self.duration, self.current_pos + offset))
        self.current_pos = new_pos
        self.current_pos_ratio = (
            self.current_pos / self.duration if self.duration > 0 else 0.0
        )

        self._running = False
        Clock.unschedule(self.update_frame)

        threading.Thread(
            target=self._background_seek, args=(new_pos, was_running), daemon=True
        ).start()

    def _background_seek(self, target_pos: float, restart_playback: bool):
        if self.decoder:
            self.decoder.pause()
            self.decoder.seek(target_pos)

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=1.0)
        self.read_thread = None

        Clock.schedule_once(lambda dt: self._on_seek_complete(restart_playback), 0)

    def _on_seek_complete(self, restart_playback: bool):
        self._seeking = False
        if restart_playback:
            self.play()
        else:
            Clock.schedule_once(self.update_frame, 0)

    def on_buffering(self, *args) -> None:
        try:
            if self.buffering:
                self.loader.loading = True
            else:
                self.loader.loading = False
        except:
            pass

    def set_volume(self, volume: float) -> None:
        if self.decoder:
            clamped_vol = max(0.0, min(1.0, volume))
            self.decoder.set_volume(clamped_vol)

    def restart(self, url: str, *args) -> None:
        """Safely stops the current video, frees memory, and starts a new one."""
        self.buffering = True
        self.stop()
        self.decoder = None

        self.current_pos = 0.0
        self.current_pos_ratio = 0.0
        self.duration = 0.0

        self.tex_y = None
        self.tex_uv = None
        self.rect.texture = None
        self.bind_uv.texture = None

        self.canvas["video_ready"] = 0.0
        self.canvas.ask_update()

        if self.filename == url:
            self.open_video()
        else:
            self.filename = url


class PlayerLayout(CRelativeLayout):
    is_fullscreen = BooleanProperty(False)

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen

        if self.is_fullscreen:
            self.size_hint_y = 1
            maximize_video()
        else:
            self.size_hint_y = None if DEVICE_TYPE == "mobile" else 1
            self.height = self.width * 9 / 16
            minimize_video()


class Player(PlayerBase):
    pass


class PlayerControls(HoverBehavior, CBoxLayout):

    master = ObjectProperty()

    _playing = BooleanProperty(False)

    progressive_width = NumericProperty()

    animation = ObjectProperty()

    duration_timestamp = StringProperty()

    current_timestamp = StringProperty()

    volume_enabled = BooleanProperty(True)

    maximized = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        super(PlayerControls, self).__init__(*args, **kwargs)
        self.animation = Animation(opacity=0, d=0.5)
        self.event = Clock.schedule_once(lambda dt: self.animation.start(self), 3)

    def element_hover(self, instance: object, pos: list, *args) -> None:
        if not self.is_visible():
            self.hover = False
        if (
            (
                (hasattr(self, "cstate") and self.cstate != "disabled")
                or (not self.disabled)
            )
            and self.hover_enabled
            and self.is_visible()
        ):

            self.hover = self.collide_point(
                *(
                    self.to_widget(*pos)
                    if not isinstance(self, RelativeLayout)
                    else self.to_parent(*self.to_widget(*pos))
                )
            )
        self.opacity = 1
        self.event.cancel()
        self.animation.cancel_all(self)
        self.on_hover()

    def on_hover(self, *args) -> None:
        if not self.hover:
            self.animation = Animation(opacity=0, d=0.5)
            self.event = Clock.schedule_once(lambda dt: self.animation.start(self), 3)

    def on_touch_down(self, *args) -> None:
        self.opacity = 1
        self.event.cancel()
        self.animation.cancel_all(self)
        self.animation = Animation(opacity=0, d=0.5)
        self.event = Clock.schedule_once(lambda dt: self.animation.start(self), 3)
        super().on_touch_down(*args)

    def on_master(self, *args) -> None:
        self.master.bind(_running=self.set_state)
        self.master.bind(_paused=self.set_state)
        self.master.bind(current_pos_ratio=self.set_progress)
        self.master.bind(duration=self.set_dt)
        self.master.bind(current_pos=self.set_ct)

    def set_dt(self, *args) -> None:
        self.duration_timestamp = time.strftime(
            "%H:%M:%S", time.gmtime(self.master.duration)
        )

    def set_ct(self, *args) -> None:
        self.current_timestamp = time.strftime(
            "%H:%M:%S", time.gmtime(self.master.current_pos)
        )

    def set_state(self, *args) -> None:
        self._playing = self.master._running and (not self.master._paused)

    def set_progress(self, *args) -> None:
        self.progressive_width = self.width * self.master.current_pos_ratio

    def play(self, *args) -> None:
        self.master.play()

    def stop(self, *args) -> None:
        self.master.stop()

    def pause(self, *args) -> None:
        self.master.pause()

    def seek_forward(self, *args) -> None:
        self.master.seek(5)

    def seek_backward(self, *args) -> None:
        self.master.seek(-5)

    def on_volume_enabled(self, *args) -> None:
        (
            self.master.set_volume(1.0)
            if self.volume_enabled
            else self.master.set_volume(0.0)
        )

    def on_maximized(self, *args) -> None:
        self.parent.toggle_fullscreen()


class PlayerButton(UIShellButton):
    pass
