import os
import sys

os.environ["devicetype"] = "mobile"

from kivy.resources import resource_add_path

sys.path.insert(0, os.path.dirname(__file__))
resource_add_path(os.path.dirname(__file__))

from kivy.clock import Clock
from kivy.core.window import Window

from kivy import platform

if platform == "win":
    os.add_dll_directory(
        os.path.join(os.path.expanduser("~"), "Downloads", "ffmpeg", "bin")
    )  # Replace with the path of your ffmpeg dll bin directory. Only for windows.

from uix.player import Player

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

    CStackLayout:

        PlayerLayout:
            id: layout

            Player:
                id: player_base
                loader: player_loading
                size_hint: 1, 1
                fit_mode: "contain"
                filename: "https://storage.googleapis.com/exoplayer-test-media-1/mp4/android-screens-10s.mp4"

            PlayerLoadingLayout:
                id: player_loading

            PlayerControls:
                master: player_base

            PlayerButton:
                icon: "overflow-menu--vertical"
                pos_hint: {"top": 1.0, "right": 1.0}
"""


class myapp(CarbonApp):
    def __init__(self, *args, **kwargs):
        # self.theme = "Gray100"
        super(myapp, self).__init__(*args, **kwargs)

    def build(self) -> CScreen:
        screen = Builder.load_string(appkv)
        return screen


if __name__ == "__main__":
    myapp().run()
