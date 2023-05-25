import pygame
from pygame import mixer as mix
import os

PLAYBACK_DIR = 'music/'

mix.init()

class ClickPlayer:
    HIGH = 1
    MID = 0.7
    LOW = 0.4
    def __init__(self, playback_dir):
        self.playback_dir = playback_dir
        self.files = os.listdir(playback_dir)
        self.current_track = 0
        self.volume = self.MID
        
    def _play(self, track_name):
        mix.music.load(self.playback_dir + track_name)
        mix.music.play()
        
    def play_next(self):
        if self.current_track + 1 < len(self.files):
            if mix.music.get_busy():
                mix.music.unload()
            self.current_track += 1
            track_name = self.files[self.current_track]
            self._play(track_name)
            print('PLAYING...', self.current_track, track_name)
        else:
            print('LAST TRACK !')
        
    def play_pause(self):
        if mix.music.get_busy():
            mix.music.pause()
            print('PAUSED...')
        else:
            mix.music.unpause()
            print('PLAYING...')
            
    def vol_up(self):
        if self.volume < self.HIGH:
            self.volume += 0.3
            mix.music.set_volume(self.volume)
            print('VOLUME:', self.volume)
        else:
            print('MAX VOLUME!')
        
    def vol_down(self):
        if self.volume > self.LOW:
            self.volume -= 0.3
            mix.music.set_volume(self.volume)
            print('VOLUME:', self.volume)
        else:
            print('MIN VOLUME!')
        
    def previous(self):
        if self.current_track > 0:
            if mix.music.get_busy():
                mix.music.unload()
            self.current_track -= 1
            track_name = self.files[self.current_track]
            self._play(track_name)
            self.play_pause()
            print('LOADED...', self.current_track, track_name)
        else:
            print('FIRST TRACK !')

def ask_user(message, options):
    options_str = {}
    allowed_nums = []
    for num, option in enumerate(options):
        options_str[str(num + 1).center(len(option))] = option
        allowed_nums.append(str(num + 1))
    while True:
        print(message)
        print(*options_str.values())
        print(*options_str.keys())
        choice = input()
        if choice in allowed_nums:
            break
        print('Неправильно!')
    return int(choice) - 1
    
def turn_off():
    mix.music.stop()
    mix.music.unload()
    
    
player = ClickPlayer(PLAYBACK_DIR)
choice = 100
controls = ('exit', 'play next', 'play/pause', 'vol+', 'vol-', 'previous and stop')
actions = (turn_off, player.play_next, player.play_pause, player.vol_up, player.vol_down, player.previous)
while choice:
    choice = ask_user('input controls', controls)
    actions[choice]()
