import pygame
import os
from pygame import mixer as mix
import tkinter as tki

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
        
    def _play(self, track_name=None):
        if track_name == None:
            track_name=self.files[self.current_track]
        mix.music.load(self.playback_dir + track_name)
        mix.music.play()
        print('PLAYING...', self.current_track, track_name)
        
    def play_next(self, event=None):
        if self.current_track + 1 < len(self.files):
            if mix.music.get_busy():
                mix.music.unload()
            self.current_track += 1
            self._play()
        else:
            print('LAST TRACK !')
        
    def play_pause(self, event=None):
        if mix.music.get_busy():
            mix.music.pause()
            print('PAUSED...')
        else:
            if mix.music.get_pos() < 0:
                self._play()
            else:
                mix.music.unpause()
                print('PLAYING...')
            
    def vol_up(self, event=None):
        if self.volume < self.HIGH:
            self.volume += 0.3
            mix.music.set_volume(self.volume)
            print('VOLUME:', self.volume)
        else:
            print('MAX VOLUME!')
        
    def vol_down(self, event=None):
        if self.volume > self.LOW:
            self.volume -= 0.3
            mix.music.set_volume(self.volume)
            print('VOLUME:', self.volume)
        else:
            print('MIN VOLUME!')
        
    def previous(self, event=None):
        if self.current_track > 0:
            if mix.music.get_busy():
                mix.music.unload()
            self.current_track -= 1
            self._play()
            self.play_pause()
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
    
def turn_off(event=None):
    mix.music.stop()
    mix.music.unload()
    exit()
    
    
player = ClickPlayer(PLAYBACK_DIR)
choice = 100
#controls = ('exit', 'play next', 'play/pause', 'vol+', 'vol-', 'previous and stop')
#actions = (turn_off, player.play_next, player.play_pause, player.vol_up, player.vol_down, player.previous)

window = tki.Tk()
window.title('alien messenger')
window.geometry('+400+50')
window.minsize(width=400, height=700)

controls = {'0': turn_off,
            '<Escape>': player.play_next,
            #'<Shift_L>': player.play_next,
            '<Tab>': player.play_pause,
            '<Up>': player.vol_up, 
            '<Down>': player.vol_down,
            'b': player.previous,
            }
for key, action_func in controls.items():
    window.bind(key, action_func)
    
window.mainloop()

#while choice:
    # for event in pygame.event.get():
#         if event.type == pygame.KEYDOWN:
#             if event.key == pygame.K_1:
#                 choice = 1
#             elif event.key == pygame.K_2:
#                 choice = 2
#             elif event.key == pygame.K_3:
#                 choice = 3
#             elif event.key == pygame.K_4:
#                 choice = 4
#             elif event.key == pygame.K_5:
#                 choice = 5
#             elif event.key == pygame.K_0:
#                 choice = 0
    #choice = ask_user('input controls', controls)
    #actions[choice]()
    
