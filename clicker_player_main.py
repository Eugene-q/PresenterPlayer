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

HORIZ_VOL_IMAGE = tki.PhotoImage(file='assets/images/horiz_vol.png',
                                 width=100,
                                 height=20,
                                 )

#initial gui elements

frame_track_list = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=5,
                            width=int(window_width / 3 * 2),
                            )
frame_add_tracks = ttk.Frame(frame_track_list)
label_file_list_header = ttk.Label(frame_add_tracks,
                                   text='СПИСОК ЗВУКОЗАПИСЕЙ',
                                   justify=tki.CENTER,
                                   )
button_add_tracks = ttk.Button(master=frame_add_tracks,
                        text='Добавить',
                        padding=3,
                        )
scrollbar_list = tki.Scrollbar(frame_track_list)
txt_tracks = tki.Text(frame_track_list, 
                        width=70,
                        height=40,
                        wrap='word',
                        yscrollcommand=scrollbar_list.set,
                        )
scrollbar_list.config(command=txt_tracks.yview)

frame_list_operations = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=5,
                            width=int(window_width / 3),
                            )
label_add_tracks_header = ttk.Label(frame_list_operations, text='УПРАВЛЕНИЕ СПИСКОМ')
button_load = ttk.Button(master=frame_list_operations,
                        text='Загрузить',
                        padding=3,
                        )
button_save = ttk.Button(master=frame_list_operations,
                        text='Сохранить',
                        padding=3,
                        )
button_clear = ttk.Button(master=frame_list_operations,
                        text='Очистить',
                        padding=3,
                        )

frame_service_signals = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=5,
                            width=int(window_width / 3),
                            )
label_service_signals_header = ttk.Label(frame_service_signals, text='СИГНАЛЫ')
button_signal_type = ttk.Button(master=frame_service_signals,
                                text='Тип\nсигнала',
                                padding=3,
                                )
frame_signal_volume = ttk.Frame(frame_service_signals)
label_signal_volume = ttk.Label(frame_signal_volume,
                            image=HORIZ_VOL_IMAGE,
                            )
scale_signal_volume = ttk.Scale(master=frame_signal_volume,
                                orient=tki.HORIZONTAL,
                                length=100,
                                from_=0,
                                to=100,
                                value=50,
                                )
button_signals_off = ttk.Button(master=frame_service_signals,
                                text='Отключить\nсигналы',
                                padding=3,
                                )
#print(button_signals_off.configure().keys())                

frame_player = ttk.Frame(window, 
                            relief=tki.GROOVE,
                            borderwidth=4,
                            padding=5,
                            width=int(window_width / 3),
                            )
label_player_header = ttk.Label(frame_player, text='ВОСПРОИЗВЕДЕНИЕ')

#placement

frame_track_list.pack(side='left', fill='both')
frame_add_tracks.pack(fill='x')
label_file_list_header.pack(side='left', fill='x')
button_add_tracks.pack(side='right')
scrollbar_list.pack(side="right", fill='y') 
txt_tracks.pack(side='left', fill='both')

frame_list_operations.pack(side='top', fill='both')
label_add_tracks_header.pack(side='top')
button_load.pack(side='left', fill='y')
button_save.pack(side='left')
button_clear.pack(side='right', fill='y')

frame_service_signals.pack(fill='both')
label_service_signals_header.pack(side='top', pady=3)
button_signal_type.pack(side='left')
frame_signal_volume.pack(side='left')
label_signal_volume.pack(fill='x')
scale_signal_volume.pack(fill='x', padx=2,)
button_signals_off.pack(side='left')

frame_player.pack(side='bottom', fill='both')
label_player_header.pack(side='top')

frame_add_tracks.pack()

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
