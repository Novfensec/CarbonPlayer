import os
import sys

os.environ["devicetype"] = "mobile"

from kivy.resources import resource_add_path

sys.path.insert(0, os.path.dirname(__file__))
resource_add_path(os.path.dirname(__file__))

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.properties import StringProperty, BooleanProperty

from kivy import platform

if platform == "win":
    os.add_dll_directory(
        os.path.join(os.path.expanduser("~"), "Downloads", "ffmpeg", "bin")
    )  # Replace with the path of your ffmpeg dll bin directory. Only for windows.

from uix.player import *

def set_softinput(*args) -> None:
    Window.keyboard_anim_args = {"d": 0.2, "t": "in_out_expo"}
    Window.softinput_mode = "below_target"


Window.on_restore(Clock.schedule_once(set_softinput, 0.1))

from kivy.lang import Builder

from carbonkivy.app import CarbonApp
from carbonkivy.uix.screen import CScreen

# import factory_registers

appkv = """
CScreen:

    CFloatLayout:

        CBoxLayout:
            padding: dp(16), dp(64)
            orientation: "vertical"
            adaptive: [False, True]
            y: layout.y - self.height
                
            CTextInputLayout:

                CTextInput:
                    id: url_input
                    text: app.url
                    hint_text: "Enter video url or path."
                CTextInputLabel:
                    text: "Video url or path"
                CTextInputTrailingIconButton:
                    icon: "restart"
                    on_press:
                        app.url = url_input.text
                        player_base.restart(app.url)

        PlayerLayout:
            id: layout
            pos_hint: {"top": 1.0, "x": 0.0}

            Player:
                id: player_base
                loader: player_loading
                size_hint: 1, 1
                fit_mode: "contain"
                # filename: "https://storage.googleapis.com/exoplayer-test-media-1/mp4/android-screens-10s.mp4"
                filename: app.url

            PlayerLoadingLayout:
                id: player_loading

            PlayerControls:
                master: player_base

            PlayerButton:
                icon: "overflow-menu--vertical"
                pos_hint: {"top": 1.0, "right": 1.0}
                text_color: "white"
                bg_color: app.background_hover
"""


class myapp(CarbonApp):

    url = StringProperty("https://storage.googleapis.com/exoplayer-test-media-1/mp4/android-screens-10s.mp4")

    _was_playing = BooleanProperty(False)

    def __init__(self, *args, **kwargs):
        # self.theme = "Gray100"
        super(myapp, self).__init__(*args, **kwargs)

    def build(self) -> CScreen:
        screen = Builder.load_string(appkv)
        return screen

    def on_resume(self, *args) -> None:
        if getattr(self, "_was_playing", False):
            self.root.ids.player_base.play()
        super().on_resume()

    def on_pause(self, *args) -> bool:
        self._was_playing = self.root.ids.player_base._running and not self.root.ids.player_base._paused
        self.root.ids.player_base.pause()
        return True

    def on_stop(self, *args) -> None:
        self.root.ids.player_base.stop()


if __name__ == "__main__":
    myapp().run()
