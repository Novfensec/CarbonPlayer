from __future__ import annotations

__all__ = ("PlayerBase", "PlayerControls", "Player")

import queue
import videonative
import threading

from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics.texture import Texture
from kivy.uix.image import AsyncImage
from kivy.uix.relativelayout import RelativeLayout
from kivy.properties import BooleanProperty, ObjectProperty, StringProperty, NumericProperty

from carbonkivy.behaviors import HoverBehavior, StateFocusBehavior
from carbonkivy.uix.boxlayout import CBoxLayout
from carbonkivy.uix.relativelayout import CRelativeLayout
from carbonkivy.uix.shell import UIShellButton
from carbonkivy.uix.loading import CLoadingLayout


class PlayerLoadingLayout(CLoadingLayout):

    loading = BooleanProperty(False)


class PlayerBase(AsyncImage):

    filename = StringProperty()

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

    def on_filename(self, *args) -> None:
        if self.filename:
            self.open_video()

    def open_video(self, *args) -> None:
        threading.Thread(target=self._background_load, daemon=True).start()

    def _background_load(self):
        """THIS RUNS IN THE BACKGROUND: Heavy network & FFmpeg initialization."""
        try:
            temp_decoder = videonative.MediaDecoder(self.filename)
            temp_decoder.start()

            first_frame = temp_decoder.get_next_frame()
            
            if first_frame is None:
                raise RuntimeError("Failed to read the first frame of the video.")

            Clock.schedule_once(
                lambda dt: self._on_video_loaded(temp_decoder, first_frame), 0
            )

        except Exception as e:
            print(f"Video Load Error: {e}")

    def _on_video_loaded(self, loaded_decoder, first_frame) -> None:
        """THIS RUNS ON THE UI THREAD: Safely updates Kivy widgets."""
        self.decoder = loaded_decoder
        
        self.height_px, self.width_px, _ = first_frame.shape

        self.texture = Texture.create(
            size=(self.width_px, self.height_px), colorfmt="rgb"
        )
        self.texture.flip_vertical()

        self.texture.blit_buffer(
            first_frame.tobytes(), colorfmt="rgb", bufferfmt="ubyte"
        )
        self.canvas.ask_update()
        self.duration = self.decoder.get_duration()
        self.fps = self.decoder.get_fps()
        self.play()

    def _reader_loop(self):
        """THIS RUNS IN THE BACKGROUND: Reads NumPy frames and puts them in the queue."""
        while self._running and self.decoder:
            frame_arr = self.decoder.get_next_frame()

            if frame_arr is None:
                if self._running:
                    self.frame_queue.put(None)
                break

            self.frame_queue.put(frame_arr.tobytes())

    def update_frame(self, dt) -> None:
        """THIS RUNS ON THE UI THREAD: Grabs bytes from the queue and draws them."""
        try:
            frame_bytes = self.frame_queue.get_nowait()

            if self.buffering:
                self.buffering = False

            if frame_bytes is None:
                self.pause()
                self.decoder.stop()
                return

            self.texture.blit_buffer(
                frame_bytes,
                size=(self.width_px, self.height_px),
                colorfmt="rgb",
                bufferfmt="ubyte",
            )
            self.canvas.ask_update()
            self.current_pos = self.decoder.get_position()
            self.current_pos_ratio = self.current_pos / self.duration

        except queue.Empty:
            if self.decoder:
                self.buffering = self.decoder.is_buffering()

    def play(self, *args) -> None:
        if self._running:
            return

        self._running = True

        if self.decoder:
            self.decoder.start()
            self.decoder.resume()

        self.read_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self.read_thread.start()

        Clock.schedule_interval(self.update_frame, 1.0 / self.fps)

    def stop(self, *args) -> None:
        self._running = False
        Clock.unschedule(self.update_frame)

        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except queue.Empty:
                break

        if self.read_thread and self.read_thread.is_alive():
            self.read_thread.join(timeout=0.5)

        if self.decoder:
            self.decoder.stop()

    def pause(self, *args) -> None:
        self._running = False 
        
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
        if not self.decoder:
            return
            
        was_running = self._running
        current_pos = self.decoder.get_position()
        
        if was_running:
            self.pause() 

        new_pos = max(0.0, current_pos + offset)
        self.decoder.seek(new_pos)

        if was_running:
            self.play()

    def on_buffering(self, *args) -> None:
        try:
            if self.buffering:
                self.loader.loading = True
            else:
                self.loader.loading = False
        except:
            pass
            

class PlayerLayout(CRelativeLayout):
    pass


class Player(PlayerBase):
    pass


class PlayerControls(HoverBehavior, CBoxLayout):

    master = ObjectProperty()

    _playing = BooleanProperty(False)

    progressive_width = NumericProperty()

    animation = ObjectProperty()

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


class PlayerButton(UIShellButton):
    pass