import os

from kivy.lang import Builder

from uix import UIX

from .player import PlayerBase, Player, PlayerButton, PlayerControls, PlayerLayout

filename = os.path.join(UIX, "player", "player.kv")
if not filename in Builder.files:
    Builder.load_file(filename)
