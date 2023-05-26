import pygame
import os
from pygame import mixer as mix
import tkinter as tki
from tkinter import ttk

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
    
def turn_off(event=None):
    mix.music.stop()
    mix.music.unload()
    exit()
    
    
player = ClickPlayer(PLAYBACK_DIR)

window = tki.Tk()
window.title('Clicker Player')
#window.geometry('+40+50')
screen_width = window.winfo_screenwidth()
screen_height = window.winfo_screenheight()
window_width = 700
window_width = 700
window.minsize(width=window_width, height=window_width)

#initial gui elements

frame_track_list = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=10,
                            width=int(window_width / 3 * 2),
                            )
label_file_list_header = ttk.Label(frame_track_list, text='СПИСОК ТРЕКОВ')

frame_add_tracks = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=10,
                            width=int(window_width / 3),
                            )
label_add_tracks_header = ttk.Label(frame_add_tracks, text='ДОБАВИТЬ ТРЕКИ')
scrollbar_list = tki.Scrollbar(frame_track_list)
txt_tracks = tki.Text(frame_track_list, 
                        width=70,
                        height=40,
                        wrap='word',
                        yscrollcommand=scrollbar_list.set,
                        )
scrollbar_list.config(command=txt_tracks.yview)

frame_service_signals = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=10,
                            width=int(window_width / 3),
                            )
label_service_signals_header = ttk.Label(frame_service_signals, text='ЗВУКОВЫЕ СИГНАЛЫ')

frame_player = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=10,
                            width=int(window_width / 3),
                            )
label_player_header = ttk.Label(frame_player, text='ВОСПРОИЗВЕДЕНИЕ')

#placement

frame_track_list.pack(side='left', fill='y')
label_file_list_header.pack(side='top')
scrollbar_list.pack(side="right", fill="y") 
txt_tracks.pack(side='left', fill='both')

frame_add_tracks.pack(side='top', fill='both')
label_add_tracks_header.pack(side='top')

frame_service_signals.pack(fill='both')
label_service_signals_header.pack(side='top')

frame_player.pack(side='bottom', fill='both')
label_player_header.pack(side='top')

controls = {'0': turn_off,
            '<Escape>': player.play_next,
            '<Shift_L>': player.play_next,
            '<Tab>': player.play_pause,
            '<Up>': player.vol_up, 
            '<Down>': player.vol_down,
            'b': player.previous,
            }
for key, action_func in controls.items():
    window.bind(key, action_func)
    
window.mainloop()
