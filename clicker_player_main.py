import pygame
from pygame import mixer as mix
import os

PLAYBACK_DIR = 'music/'
music_files = os.listdir(PLAYBACK_DIR)

#pygame.init()
mix.init()

mix.music.load(PLAYBACK_DIR + music_files[0])
mix.music.play()

input('press Enter')

mix.music.fadeout(1000)
mix.music.unload()