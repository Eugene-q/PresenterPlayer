# -*- coding: utf-8 -*-

import audioread
import pdb
import json
import keyboard
import sys
import os
import codecs
from collections import deque
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
import assets.icons
from superqt import QRangeSlider
from shutil import copyfile, rmtree
from time import sleep
from threading import Thread, get_ident
from threading import active_count as active_threads

#sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
#pyrcc5 -o icons.py icons.qrc
VALID_SYMBOL_CODES = (tuple(chr(s) for s in range(1040, 1104)) + 
                        tuple(chr(s) for s in range(128)) + ('ё', 'Ё'))
                        
BASE_DIR = os.path.dirname(__file__)
USER_HOME_DIR = os.path.expanduser('~')
USER_MUSIC_DIR = os.path.join(USER_HOME_DIR, 'Music')

SONG_ITEM_UI_PATH = os.path.join(BASE_DIR, 'GUI/songitem.ui')
SONG_LIST_UI_PATH = os.path.join(BASE_DIR, 'GUI/songList.ui')
MAIN_WINDOW_UI_PATH = os.path.join(BASE_DIR, 'GUI/main_window.ui')
OPTIONS_DIALOG_UI_PATH = os.path.join(BASE_DIR, 'GUI/options.ui')
DEFAULT_SIGNAL_PATH = os.path.join(BASE_DIR, 'assets/signal.wav')

DEFAULT_PLAYBACK_DIR = os.path.join(USER_MUSIC_DIR, 'song_lists/new_songlist_music/')
DEFAULT_SAVE_DIR = os.path.join(USER_MUSIC_DIR, 'song_lists/')
SONG_LIST_EXTENSION = '.sl'
DEFAULT_SONGLIST_NAME = 'New_songlist'

OPTIONS_FILE_PATH = os.path.join(BASE_DIR, 'assets/options.json')
DEFAULT_OPTIONS = {'last_playlist_path': os.path.join(DEFAULT_SAVE_DIR, 
                                            DEFAULT_SONGLIST_NAME + SONG_LIST_EXTENSION),
                   'signals_enabled': False,
                   'signals_volume': 50,
                   'always_show_automations': False,
                   'autoplay_fforw': False,
                   'autoplay_rew': False,
                   'clicker_enabled_in_list_mode': True,
                }

CLEAR_WARNING = 'Все несохранённые изменения будут утеряны! Очистить список?'
LOAD_WARNING = 'Загружаемый список заменит существующий.\nВсе несохранённые изменения будут утеряны. Продолжить?'
DELETE_PLAYING_WARNING = 'Нельзя удалить то, что сейчас играет!'
SOURCE_DELETE_WARNING = '''Песни {} больше нет в списке, но файл с ней ещё остался.
Если удалить файл, вы, возможно, не сможете восстановить его.
Если файл оставить, вы потом сможете снова добавить его в список\n
Cancel - оставить файл. Ок - удалить '''
LIST_DELETE_WARNING = 'Полностью удалить список и связанные с ним файлы?'

CHANGE_POS_STEP = 250

STOPED = 0
PLAYING = 1
PAUSED = 2

PLAY_ONE = 0
REPEAT_ONE = 1
PLAY_ALL = 2
REPEAT_ALL = 3
    

OK = 1024

BASE_WAVEFORM_DISPLAY_WIDTH = 1920
PLAYBACK_SLIDER_WIDTH_OFFSET = 92
PLAYBACK_SLIDER_WAVEFORM_OFFSET = 10
WAVEFORM_AVERAGING_FRAME_WIDTH = 3
PLAYBACK_SLIDER_HEIGHT = 27

LIST_ITEM_HEIGHT = 28


class OptionsDialog(QtWidgets.QDialog):
    def __init__(self, options_file_path, player):
        super().__init__()
        
        uic.loadUi(OPTIONS_DIALOG_UI_PATH, self)

        self.options_file_path = options_file_path
        self.player = player
        
        self.load()
        self.cancel()
        
        self.sliderSignalsVol.sliderReleased.connect(self.test_signal_vol)
        self.buttonSave.clicked.connect(self.save)
        self.buttonCancel.clicked.connect(self.cancel)
    
    def load(self):
        if os.path.exists(self.options_file_path):
            with open(self.options_file_path, 'r', encoding='utf-8') as options_file:
                options_set = json.load(options_file) or DEFAULT_OPTIONS
        else:
            options_set = DEFAULT_OPTIONS
        self.last_playlist_path = options_set.get('last_playlist_path')
        self.signals_volume = options_set.get('signals_volume')
        self.checkBoxEnableSignals.setChecked(options_set.get('signals_enabled'))
        self.checkBoxShowAutomations.setChecked(options_set.get('always_show_automations'))
        self.checkBoxAutoplayFforw.setChecked(options_set.get('autoplay_fforw'))
        self.checkBoxAutoplayRew.setChecked(options_set.get('autoplay_rew'))
        self.checkBoxKeyControlsEnable.setChecked(options_set.get('clicker_enabled_in_list_mode'))

    def save(self):
        self.last_playlist_path = self.player.list.save_file_path
        self.signals_volume = self.sliderSignalsVol.value()
        options_set = {'last_playlist_path': self.last_playlist_path,
                       'signals_volume': self.signals_volume,
                       'signals_enabled': self.checkBoxEnableSignals.isChecked(),
                       'always_show_automations': self.checkBoxShowAutomations.isChecked(),
                       'autoplay_fforw': self.checkBoxAutoplayFforw.isChecked(),
                       'autoplay_rew': self.checkBoxAutoplayRew.isChecked(),
                       'clicker_enabled_in_list_mode': self.checkBoxKeyControlsEnable.isChecked(),
                   }
        with open(self.options_file_path, 'w', encoding='utf-8') as options_file:
            json.dump(options_set, options_file, indent=4)
        self.player.show_automations(self.checkBoxShowAutomations.isChecked())
        self.player.setFocus()
        self.hide()
        
    def cancel(self):
        self.sliderSignalsVol.setValue(int(self.signals_volume))
        self.checkBoxEnableSignals.setChecked(self.checkBoxEnableSignals.isChecked())
        self.player.setFocus()
        self.hide()
    
    def test_signal_vol(self,):
        if self.checkBoxEnableSignals.isChecked():
            volume = self.sliderSignalsVol.value()
            self.player.play_signal(enabled=True, 
                                    volume=volume)
       

class SongWidget(QtWidgets.QWidget):
    def __init__(self, parent,
                       id,
                       path,
                       name,
                       length,
                       file_type='.mp3',
                       volume=100,
                       start_pos=0,
                       end_pos=0,
                       repeat=False,
                       fade_range=(0, 0),
                       muted=False,
                       waveform=[]
                       ):
        super().__init__()
        self.id = id
        self.path = path
        self.name = name
        self.file_type = file_type
        self.volume = volume
        self.length = length
        self.start_pos = start_pos
        self.end_pos = end_pos or length
        self.repeat = repeat
        self.faded = False 
        fade_in, fade_out = fade_range
        if not fade_out:
            fade_out = self.end_pos
        self.fade_range = (fade_in, fade_out)
        self.set_fading(self.fade_range)
        self.range_limited = False
        self.set_playback_range((self.start_pos, self.end_pos))
        self.muted = muted
        self.waveform = waveform
        self.song_list = parent
        
        uic.loadUi(SONG_ITEM_UI_PATH, self)
        self.labelSongName.setText(name)
        self.labelSongName.setToolTip(name)
        
        self.lineNewSongName.returnPressed.connect(self.save_name)
        self.lineNewSongName.hide()
        #print('song created. fade range:', self.fade_range)
        
    def rename(self):
        self.labelSongName.hide()
        self.lineNewSongName.show()
        self.lineNewSongName.setText(self.name)
        self.lineNewSongName.selectAll()
        self.lineNewSongName.setFocus()
        self.song_list.player.enable_controls(False)
        
    def save_name(self):
        self.name = self.lineNewSongName.text()
        self.labelSongName.setText(self.name)
        self.song_list.set_saved(False)
        self.normal_mode()
        
    def normal_mode(self):
        self.lineNewSongName.clearFocus()
        self.lineNewSongName.hide()
        self.labelSongName.show()
        self.song_list.player.enable_controls()
    
    def set_playback_range(self, playback_range):
        self.start_pos, self.end_pos = playback_range
        self.range_limited = (self.start_pos != 0 or
                          self.end_pos != self.length) or False
            
    def set_fading(self, fade_range):
        fade_in, fade_out = fade_range
        if fade_in < self.start_pos:
            fade_in = self.start_pos
        if fade_out > self.end_pos:
            fade_out = self.end_pos
        if fade_in > fade_out:
            fade_in = fade_out
        self.faded = (fade_in > self.start_pos or
                     fade_out < self.end_pos) or False
        self.fade_range = (fade_in, fade_out)
        #print('SET FADING', self.name[:10], 'faded:', self.faded, self.fade_range)
        

class SongListWidget(QtWidgets.QWidget):
    def __init__(self, player):
        super().__init__()
        
        #GUI settings
        uic.loadUi(SONG_LIST_UI_PATH, self)
        self.list = SongList(self)
        self.layoutSongList.addWidget(self.list)
        self.layoutSongList.layoutBottomMargin = 0
        
        self.lineListHeader.hide()
        self.lineListHeader.returnPressed.connect(self.save_list_name)
        self.buttonListHeader.clicked.connect(self.rename_mode)
        self.buttonListHeader.setToolTip(self.buttonListHeader.text())
        self.buttonListHeader.setStyleSheet("text-align:left;")
        self.buttonAddTrack.clicked.connect(self.add_songs)  
        self.buttonSaveList.clicked.connect(self.save)
        self.buttonSaveListAs.clicked.connect(self.save_as)
        self.buttonLoadList.clicked.connect(self.load)
        self.buttonClearList.clicked.connect(self.clear)
        self.buttonDeleteList.clicked.connect(self.delete)
        
        self.player = player
        #self.repeat = PLAY_ALL
        self.renamed_song = None
        self.id_source = 0
        self.saved = True
        self.playback_dir = DEFAULT_PLAYBACK_DIR
        if not os.path.exists(DEFAULT_SAVE_DIR):
            os.mkdir(DEFAULT_SAVE_DIR)
        self.save_file_path = ''
        self.selected = 0               #selected song index
        self.playing = self.selected    #playing song index
        self.set_current_row(0)
    
    def scale_number(self, unscaled, to_min, to_max, from_min, from_max):
        return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min
        
    def add_songs(self, filenames=[], songs_info=[]): 
        list_was_empty = self.is_empty() 
        if songs_info:                   # Добавление песен из загруженного списка
            for info in songs_info:
                song_widget = SongWidget(parent=self,
                                        id=info.get('id'),
                                        path=info.get('path'),
                                        name=info.get('name'),
                                        file_type=info.get('file_type'),
                                        volume=info.get('volume'),
                                        length=info.get('length'),
                                        start_pos=info.get('start_pos'),
                                        end_pos=info.get('end_pos'),
                                        repeat=info.get('repeat'),
                                        fade_range=info.get('fade_range'),
                                        muted=info.get('muted'),
                                        waveform=info.get('waveform')
                                        )
                self.add_song_widget(song_widget)
        else:
            if not filenames:           # Добавление песен по кнопке +
                filepaths = QtWidgets.QFileDialog.getOpenFileNames(self, 
                                                        'Добавить дорожки', 
                                                        USER_MUSIC_DIR, 
                                                        'Music Files (*.mp3 *.wav)',
                                                        )[0]
                self.player.setFocus()
                filenames = []
                current_playback_filenames = self.get_playback_dir_filenames()
                #print('Playback filenames:', current_playback_filenames)
                for filepath in filepaths:
                    filedir, filename = os.path.split(filepath)
                    improved_filename = self.improve_filename(filename)
                    if improved_filename:
                        filename = improved_filename
                        pass            # TODO Окно предупреждения об удалении недопустимых символов
                    filenames.append(filename)
                    if filename not in current_playback_filenames:
                        copyfile(filepath, os.path.join(self.playback_dir, filename))
        
            for song_filename in filenames:
                song_file_path = os.path.join(self.playback_dir, song_filename)
                with audioread.audio_open(song_file_path) as audio_file:
                    #print('Unsupported sound file!')#TODO Сделать окно предупреждения
                    channels = audio_file.channels 
                    samplerate = audio_file.samplerate
                    duration = audio_file.duration
                    print(channels, samplerate, duration)
                    print('total samples:', samplerate * duration)
                    width = (BASE_WAVEFORM_DISPLAY_WIDTH - PLAYBACK_SLIDER_WIDTH_OFFSET - 
                                    PLAYBACK_SLIDER_WAVEFORM_OFFSET)
                    print('WIDTH:', width)
                    amplitude = PLAYBACK_SLIDER_HEIGHT
                    step = int((samplerate * duration) / width) * channels
                    read_pos = 0
                    samples = []
                    tail = 0
                    for buf in audio_file:
                        read_pos = tail or 0
                        buf_int = memoryview(buf).cast('h')
                        while (read_pos + 1) < len(buf_int):
                            channels_bytes = []
                            for i in range(channels):
                                channel_bytes = buf_int[read_pos]
                                channels_bytes.append(channel_bytes)
                                read_pos += 1
                            sample = abs(max(channels_bytes))
                            #sample = int(self.scale_number(sample, 0, 26, 0, max_sample))#32768))
                            samples.append(sample)
                            read_pos += step
                        tail = abs(read_pos - len(buf_int) - 1)
                    samples_averaged = []
                    frame = deque(maxlen=WAVEFORM_AVERAGING_FRAME_WIDTH)
                    max_sample = max(samples)
                    for sample in samples:
                        sample = int(self.scale_number(sample, 0, PLAYBACK_SLIDER_HEIGHT, 0, max_sample))
                        frame.append(sample)
                        if len(frame) >= WAVEFORM_AVERAGING_FRAME_WIDTH:
                            sample_averaged = int(sum(frame) / WAVEFORM_AVERAGING_FRAME_WIDTH)
                            samples_averaged.append(sample_averaged)
                length = int(duration * 1000)
                song_name, file_type = os.path.splitext(song_filename)
                song_widget = SongWidget(parent=self,
                                         id=self.get_id(),
                                         path=song_file_path,
                                         name=song_name,
                                         file_type=file_type,
                                         length=length,
                                         waveform=samples_averaged
                                         )
                self.add_song_widget(song_widget)
        if filenames:
            self.set_saved(False)
            if list_was_empty:
                self.player.enable(True)
                self.player.load(self.song(0))
                self.set_row(0)
    
    def add_song_widget(self, song_widget):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(1, LIST_ITEM_HEIGHT)) #width based on parent, height = 28
        self.list.addItem(item)
        self.list.setItemWidget(item, song_widget)
        self.saved = False
    
        song_widget.buttonPlay.clicked.connect(self.player.play_pause)
        song_widget.buttonRepeat.clicked.connect(self.player.set_repeat)
        song_widget.buttonDelete.clicked.connect(self.delete_song_widget)
        song_widget.buttonMute.clicked.connect(self.mute_song)
        song_widget.buttonMute.setChecked(song_widget.muted)
        if song_widget.muted:
            song_widget.buttonPlay.setDisabled(True)

    def delete_song_widget(self):
        #delete_index = self.list.currentRow()
        delete_index = self.list.get_song_index(self.sender().parent())
        if delete_index == self.playing and self.player.state is not STOPED:
            self.show_message_box(DELETE_PLAYING_WARNING, cancel=False)
        elif self.show_message_box('Точно удалить?') == OK:
                if delete_index < self.playing:
                    self.playing -= 1
                self.list.takeItem(delete_index)
                if self.is_empty():
                    self.player.enable(False)
                #     self.player.buttonSaveList.setDisabled(True)
                self.set_saved(False)
    
    def save_list_name(self):
        new_name = self.lineListHeader.text()
        new_save_file_path = os.path.join(os.path.dirname(self.save_file_path),
                                            new_name+SONG_LIST_EXTENSION).lower()
        old_save_file_path = os.path.normpath(self.save_file_path.lower())
        new_save_file_path = os.path.normpath(new_save_file_path.lower())
        #print('OLD:', old_save_file_path)
        #print('NEW:', new_save_file_path)
        if new_save_file_path == old_save_file_path:
            self.normal_mode()
            return
        new_save_file_path = os.path.abspath(new_save_file_path)
        self.save_as(new_save_file_path)
        os.remove(old_save_file_path)
        self.player.eject()
        rmtree(self.get_playback_dir_path(old_save_file_path))
        self.normal_mode()
        self.buttonListHeader.setText(new_name)
        self.buttonListHeader.setToolTip(new_name)
        self.player.load(self.song(self.playing))
    
    def save(self):
        if not self.saved:
            songs_info = []
            for song in self.list.get_all_songs():
                songs_info.append(self.list.get_song_info(song))
            #print('Save file path:', self.save_file_path)
            with open(self.save_file_path, 'w') as save_file:
                json.dump(songs_info, save_file, indent=4)
                #json.dump(list(reversed(songs_info)), save_file, indent=4)
            song_filenames = [os.path.basename(song_info.get('path')) for song_info in songs_info]
            for filename in self.get_playback_dir_filenames():
                if filename not in song_filenames:
                    if self.show_message_box(SOURCE_DELETE_WARNING.format(filename.partition('.')[0])) == OK:
                        os.remove(os.path.join(self.playback_dir, filename))#TODO Добавить кнопки Удалить все и Сохранить все или чекбокс Применить ко всем.
            self.set_saved()
            print('saved')
        else:
            print('not saved')
    
    def save_as(self, save_file_path=''):
        if not save_file_path:
            save_file_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Файл сохранения',
                                     os.path.join('.', DEFAULT_SAVE_DIR), 'SongList File (*.sl)')[0]
            self.player.setFocus()
        if save_file_path == self.save_file_path:
            print('called SAVE')
            self.save()
        elif save_file_path:
            music_dir_path = self.get_playback_dir_path(save_file_path)
            #if save_file_path:
            songs_info = []
            if os.path.exists(music_dir_path):
                rmtree(music_dir_path)#TODO Предупреждение, что такой список уже есть.
            os.mkdir(music_dir_path)
            self.playback_dir = music_dir_path
            for song in self.list.get_all_songs():
                new_song_path = os.path.join(music_dir_path, song.name + song.file_type)
                copyfile(song.path, new_song_path)
                song.path = new_song_path
                songs_info.append(self.list.get_song_info(song))
            with open(save_file_path, 'w') as save_file:
                json.dump(songs_info, save_file, indent=4)
                #json.dump(list(reversed(songs_info)), save_file, indent=4)
            self.save_file_path = save_file_path
            self.set_saved()
        
    def set_saved(self, saved=True):
        self.saved = saved
        if saved:
            self.labelSaveSign.setText('')
            list_name = os.path.basename(self.save_file_path).partition('.')[0]
            #print('list name for button:', list_name)
            self.buttonListHeader.setText(list_name)
            self.buttonListHeader.setToolTip(list_name)
            self.buttonSaveList.setDisabled(True)
        else:
            self.labelSaveSign.setText('*')
            self.buttonSaveList.setEnabled(True)
                  
    def load(self, load_file_path=''):
        print('LOAD SONGLIST')
        if self.is_empty() or self.show_message_box(LOAD_WARNING) == OK:
            if not load_file_path:
                load_file_path = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                        'Загрузка списка песен', 
                                                        os.path.join(USER_MUSIC_DIR, 'song_lists'), 
                                                        'SongList File (*.sl)',
                                                        )[0]
                self.player.setFocus()
            if load_file_path:
                print('file path:', load_file_path)   
                with open(load_file_path, 'r') as load_file:
                    songs_info = json.load(load_file)
                if not self.is_empty():
                    self.player._stop()
                    self.player.eject()
                    self.clear(silent=True)            
                if songs_info:
                    self.add_songs(songs_info=songs_info)
                    self.set_row(0, playing=True)
                    self.player.load(self.song(self.playing))
                    self.player.enable()
                else:
                    self.player.enable(False)
                self.save_file_path = load_file_path
                self.playback_dir = self.get_playback_dir_path(load_file_path)
                self.set_saved()
            
    def clear(self, silent=False):
        result = False
        if not self.is_empty():
            if silent or self.show_message_box(CLEAR_WARNING) == OK:
                self.list.clear()
                self.set_saved()
                self.player.eject()
                self.player.enable(False)
                result = True
            else:
                self.player.enable()
        self.player.setFocus()
        return result

    def delete(self):
        if self.show_message_box(LIST_DELETE_WARNING) == OK:
            self.player._stop()
            self.player.eject()
            self.clear(silent=True)
            os.remove(self.save_file_path)
            rmtree(self.get_playback_dir_path(self.save_file_path))
            save_name = DEFAULT_SONGLIST_NAME
            while True:
                save_file_path = os.path.join(DEFAULT_SAVE_DIR, save_name + SONG_LIST_EXTENSION)
                if os.path.exists(save_file_path):
                    with open(save_file_path) as save_file:
                        if json.load(save_file):
                            save_name += '_копия'
                        else:
                            break
                else:
                    break
            self.save_file_path = save_file_path
            music_dir_path = self.get_playback_dir_path(self.save_file_path)
            if os.path.exists(music_dir_path):
                rmtree(music_dir_path)
            os.mkdir(music_dir_path)
            self.playback_dir = music_dir_path
            self.set_saved(False)
            self.save()
        self.player.setFocus()
            
    def set_row(self, target, playing=False):
        if type(target) != int:
            row = self.list.get_song_index(target)    
        else:
            row = target
        print('SET ROW from', self.list.currentRow(), 'to', row)
        self.list.setCurrentRow(row)
        if playing:
            self.playing = row
    
    def change_row(self, row):
        print()
        print('CHANGE ROW')
        song = self.song(row)
        self.selected = row
        print('SELECTED SONG INDEX:', self.selected)
        print('Player_state:', self.player.state)
        if song:
            if self.player.state is STOPED:
                if song == self.song(self.playing):
                    if song.repeat:
                        self.player.switch_repeat_to(REPEAT_ONE)
                    else:
                        self.player.switch_repeat_to(self.player.prev_repeat_mode)
                else:
                    self.playing = row
                    self.player.eject()
                    self.player.load(self.song(self.playing))
                    self.player.switch_repeat_to(self.player.prev_repeat_mode)
        else:
            print('Song widget not detected!') 
        if self.renamed_song:
            self.renamed_song.normal_mode()
        self.normal_mode()
        
    def rename_song(self, list_item=None):
        self.renamed_song = self.list.itemWidget(list_item)
        self.renamed_song.rename()

    def mute_song(self):
        muted_song = self.sender().parent()
        muted_song.muted = not muted_song.muted
        self.set_saved(False)
        if muted_song.muted:
            muted_song.buttonPlay.setDisabled(True)
            if muted_song == self.song(self.selected):
                self.player.enable(False, just_playback=True)
            if muted_song == self.song(self.playing) and self.player.state == PLAYING:
                self.player._stop()
        else:
            muted_song.buttonPlay.setEnabled(True)
            self.player.enable(just_playback=True)
        
    def rename_mode(self):
        self.player.enable_controls(False)
        self.buttonListHeader.hide()
        self.lineListHeader.show()
        self.lineListHeader.setText(self.buttonListHeader.text())
        self.lineListHeader.selectAll()
        self.lineListHeader.setFocus()

    def normal_mode(self):
        self.player.enable()
        self.buttonListHeader.show()
        self.lineListHeader.hide()
        self.lineListHeader.clearFocus()
        self.player.setFocus()
        
    def show_message_box(self, message, cancel=True):
        message_box = QtWidgets.QMessageBox()
        button_ok = QtWidgets.QMessageBox.Ok
        button_cancel = QtWidgets.QMessageBox.Cancel
        if cancel:
            message_box.setStandardButtons(button_ok | button_cancel)
        else:
            message_box.setStandardButtons(button_ok)
        message_box.setText(message)
        return message_box.exec()
        
    def get_playback_dir_filenames(self):
        return [f_name.strip() for f_name in os.listdir(self.playback_dir
                                    ) if not f_name.startswith('.')]

    def improve_filename(self, filename):
        print('FILE NAME:', filename)
        if filename.isascii():
            result = False
        else:
            valid_filename_symbols = []
            for s in filename:
                if s not in VALID_SYMBOL_CODES:
                    s = '#'
                valid_filename_symbols.append(s)
            result = ''.join(valid_filename_symbols)
        return result

    def get_playback_dir_path(self, list_file_path):
        dirname, filename = os.path.split(list_file_path)
        return os.path.join(dirname, filename.partition('.')[0] + '_music')
              
    def get_id(self):   # TODO Переписать как генератор
        id = self.id_source
        self.id_source += 1
        return id
    
    def is_empty(self):
        return not self.list.count() > 0 or False
            
    def set_current_row(self, row):
        self.list.setCurrentRow(row)
        
    def get_song(self, direction=''):
        song = None
        if self.player.state == PLAYING or self.player.state == PAUSED:
            song_index = self.playing
        else:
            song_index = self.selected
            
        if direction == 'previous':
            in_list_range = song_index > 0
            increment = -1
            message = 'FIRST TRACK !'
        elif direction == 'next':
            in_list_range = song_index + 1 < self.list.count()
            increment = 1
            message = 'LAST TRACK !'
        else: #current song
            in_list_range = True
            increment = 0
        
        if in_list_range:
            new_song_index = song_index + increment
            self.set_row(new_song_index)
            self.playing = new_song_index
            #self.playing_song = self.list.get_song_by_index(new_song_index)
            print('List -- GET SONG --')
            print('new_song_index:', self.playing)
            song = self.song(self.playing)
        else:
            print(message)
        return song #возвращает None, если нет следующей или предыдущей песни
        
    def song(self, index):
        return self.list.get_song_by_index(index)
        
    
class SongList(QtWidgets.QListWidget):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        
        #GUI settings
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAcceptDrops(True)
        self.dragEnabled()
        self.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        #self.setSortingEnabled(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet("QListWidget::item:selected{background:yellow;}")
        
        self.currentRowChanged.connect(self.widget.change_row)
        self.itemDoubleClicked.connect(self.widget.rename_song)
        
    def dragEnterEvent(self, event):
        #print('List: ACCEPT!!')
        #print('drag track num =', self.player.current_track_num)
        #event.accept()
        event.acceptProposedAction()
        
    def dropEvent(self, event):
        print("List: DROP!!")
        raw_drop_index = self.indexAt(event.pos()).row()
        drop_indicator = self.dropIndicatorPosition()
        from_index = self.currentRow()
        if raw_drop_index > from_index:
            drop_index = raw_drop_index + (drop_indicator - 2)
        else:
            drop_index = raw_drop_index + (drop_indicator - 1)
        if drop_index != from_index:
            playing = self.widget.playing
            print('playing song index', playing)
            if playing == from_index:
                self.widget.playing = drop_index
            elif from_index < playing and drop_index >= playing:
                self.widget.playing -= 1
            elif from_index > playing and drop_index <= playing:
                self.widget.playing += 1
            self.widget.set_saved(False)
            print('drop indicator position:', self.dropIndicatorPosition())
            print('from index', from_index)
            print('drop index', drop_index)
            print('playing =', self.widget.playing)
            super().dropEvent(event)
        
    def get_all_songs(self, info=False):
        songs = []
        for i in range(self.count()):
            item = self.item(i)
            song = self.itemWidget(item)
            if info:
                songs.append(self.get_song_info(song))
            else:
                songs.append(song)
        return songs
        
    def get_song_index(self, selected_song):
        for index, song in enumerate(self.get_all_songs()):
            if song == selected_song:
                return index
                    
    def get_song_by_index(self, index):
        item = self.item(index)
        if item:
            song = self.itemWidget(item)
            return song
    
    def get_song_info(self, song):
        #waveform = song.waveform or []
        song_info = {'id': song.id,
                    'path': song.path,
                    'name': song.name,
                    'file_type': song.file_type,
                    'volume': song.volume,
                    'length': song.length,
                    'start_pos': song.start_pos,
                    'end_pos': song.end_pos,
                    'repeat': song.repeat,
                    'fade_range': song.fade_range,
                    'muted': song.muted,
                    'waveform': song.waveform#''.join([str(sample) for sample in waveform]),
        }
        return song_info
        
                    
class ClickerPlayerApp(QtWidgets.QMainWindow):
    START_VOLUME = 50
    MAX_VOL = 100
    MIN_VOL = 0
    VOLUME_STEP = 5
    end_of_playback = QtCore.pyqtSignal()
    
    def __init__(self,):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        #self.setStyleSheet("#centralwidget{background-color:green}")
        
        self.controls = {QtCore.Qt.Key_Escape: self.play_next,
                         QtCore.Qt.Key_Shift: self.play_next,
                         #QtCore.Qt.Key_Tab: self.play_pause, #tab_shortcut вместо этого.
                         QtCore.Qt.Key_Space: self.play_pause,
                         QtCore.Qt.Key_Up: self.vol_up, 
                         QtCore.Qt.Key_Down: self.vol_down,
                         QtCore.Qt.Key_B: self.play_previous,
                         1048: self.play_previous,
                         QtCore.Qt.Key_Left: self.step_rewind, 
                         QtCore.Qt.Key_Right: self.step_fforward,
                         QtCore.Qt.Key_Z: self.qlist_info,
                         }
        self.controls_enabled = True
        
        self.PLAY_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/play.png'))
        self.PAUSED_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/pause.png'))
        self.START_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/start.png'))
        self.END_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/end.png'))
        self.FADEIN_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/fadein.png'))
        self.FADEOUT_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/fadeout.png'))
        self.PLAY_ONE_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/dont_repeat_one.png'))
        self.REPEAT_ONE_ICON = QtGui.QIcon(QtGui.QPixmap(':/player/icons/repeat_one.png'))
        self.PLAY_ALL_ICON = QtGui.QIcon(QtGui.QPixmap(':/player/icons/dont_repeat.png'))
        self.REPEAT_ALL_ICON = QtGui.QIcon(QtGui.QPixmap(':/player/icons/repeat.png'))
        
        self.REPEAT_MODES = {PLAY_ONE: {'checked': False,
                                   'text': 'Play one',
                                   'icon':  self.PLAY_ONE_ICON,
                                  },
                        REPEAT_ONE: {'checked': True,
                                     'text': 'Repeat one',
                                     'icon':  self.REPEAT_ONE_ICON,
                                  },
                        PLAY_ALL: {'checked': False,
                                   'text': 'Play all',
                                   'icon':  self.PLAY_ALL_ICON,
                                  },
                        REPEAT_ALL: {'checked': True,
                                     'text': 'Repeat all',
                                     'icon':  self.REPEAT_ALL_ICON,
                                  },
                       }                              
        self.save_dir = DEFAULT_SAVE_DIR
        
        self.deck_L = QMediaPlayer()
        self.deck_R = QMediaPlayer()
            
        self.start_pos = 0
        self.allow_playback_update = True
        self.allow_volume_update = True
        self.playback_update_thread = None
        self.volume_update_thread = None
        self.high_acuracy = False
        self.song_volume = 100
        self.fade_raitos = (0, 0)
        self.master_volume = self.START_VOLUME
        #self.signals_volume = 50
        #self.signals_enabled = False
        self.signal = QMediaPlayer() #mixer.Sound(DEFAULT_SIGNAL_PATH)
        content = QMediaContent(QUrl.fromLocalFile(DEFAULT_SIGNAL_PATH))
        self.signal.setMedia(content)
        self.state = STOPED
        self.enabled = True
        self.repeat_mode = PLAY_ALL
        self.prev_repeat_mode = self.repeat_mode
        self.waveform = []
        
        self.options = OptionsDialog(OPTIONS_FILE_PATH, self)
        self.presentation_mode = False
        #self.enable_presentation_mode()
        
        self.end_of_playback.connect(self.play_next)
        
        self.buttonOptions.clicked.connect(self.options.show)
        self.buttonPrevious.clicked.connect(self.play_previous)
        self.buttonStop.clicked.connect(self._stop)
        self.buttonPlay.clicked.connect(self.play_pause)
        self.buttonPause.clicked.connect(self.play_pause)
        self.buttonNext.clicked.connect(self.play_next)
        
        self.buttonRepeat.clicked.connect(self.set_repeat)
        self.switch_repeat_to(PLAY_ALL)
        
        self.buttonAutomations.clicked.connect(self.show_automations)
        
        self.buttonReset.clicked.connect(self.reset_song_settings)
        
        self.buttonPresentationMode.clicked.connect(self.enable_presentation_mode)
        
        self.sliderMasterVol.valueChanged.connect(self.master_vol_change)
        self.sliderSongVol.valueChanged.connect(self.song_vol_change)
        self.sliderSongVol.sliderPressed.connect(self.deny_volume_automation)
        self.sliderSongVol.sliderReleased.connect(self.song_vol_write)
        
        self.sliderPlaybackPos.resize(self.width() - PLAYBACK_SLIDER_WIDTH_OFFSET, PLAYBACK_SLIDER_HEIGHT)
        self.sliderPlaybackPos.sliderPressed.connect(self.deny_playback_automation)
        self.sliderPlaybackPos.sliderReleased.connect(self.change_pos)
        self.labelCurrentPosMs.hide()
        
        self.sliderFadeRange = QRangeSlider()
        self.sliderFadeRange.setOrientation(QtCore.Qt.Horizontal)
        self.sliderFadeRange.sliderReleased.connect(self.change_fade_range)
        self.buttonSetFadeIn = QtWidgets.QToolButton()
        self.buttonSetFadeIn.setIcon(self.FADEIN_ICON)
        self.buttonSetFadeIn.setFixedSize(48, 25)
        self.buttonSetFadeOut = QtWidgets.QToolButton()
        self.buttonSetFadeOut.setIcon(self.FADEOUT_ICON)
        self.buttonSetFadeOut.setFixedSize(48, 25)
        
        self.layoutVolumeRange.addWidget(self.buttonSetFadeIn)
        self.layoutVolumeRange.addWidget(self.sliderFadeRange)
        self.layoutVolumeRange.addWidget(self.buttonSetFadeOut)
        self.buttonSetFadeIn.clicked.connect(self.set_fade_range)
        self.buttonSetFadeOut.clicked.connect(self.set_fade_range)
        
        self.sliderPlaybackRange = QRangeSlider()
        self.sliderPlaybackRange.setOrientation(QtCore.Qt.Horizontal)
        self.sliderPlaybackRange.sliderReleased.connect(self.change_range)
        self.buttonSetStart = QtWidgets.QToolButton()
        self.buttonSetStart.setIcon(self.START_ICON)
        self.buttonSetStart.setFixedSize(48, 25)
        self.buttonSetEnd = QtWidgets.QToolButton()
        self.buttonSetEnd.setIcon(self.END_ICON)
        self.buttonSetEnd.setFixedSize(48, 25)
        
        self.layoutPlaybackRange.addWidget(self.buttonSetStart)
        self.layoutPlaybackRange.addWidget(self.sliderPlaybackRange)
        self.layoutPlaybackRange.addWidget(self.buttonSetEnd)
        self.buttonSetStart.clicked.connect(self.set_range)
        self.buttonSetEnd.clicked.connect(self.set_range)
        
        self.toolButton.clicked.connect(self.just_play)
        
        self.show_automations(False)
        
        self.list = SongListWidget(self)
        self.layoutSongList.addWidget(self.list)
        
        self.tab_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Tab), self)
        self.tab_shortcut.activated.connect(self.play_pause)#пока костыль в play_pause для отключения ТАБ при
                                                            #пустом списке.
        # попытка сгенерировать событие нажатия ТАБ и передать его в keyPressEvent, чтобы обрабатывалось
        # вместе с другими клавишами. Непонятно, почему ТАБ не генерит keyPressEvent нормально?
        #self.tab_shortcut.activated.connect(lambda: self.keyPressEvent(
                                                   # QtGui.QKeyEvent(type=QtCore.QEvent.KeyPress, 
                                                                    #key=QtCore.Qt.Key_Tab,
                                                                   # modifiers=[])
                                                    #))
        
        if not os.path.exists(self.options.last_playlist_path):
            self.list.save_as(DEFAULT_SAVE_DIR + 
                                   DEFAULT_SONGLIST_NAME + 
                                   SONG_LIST_EXTENSION)
        else:
            self.list.load(self.options.last_playlist_path)
            
        if self.list.is_empty():
            self.enable(False)
        else:
            self.load(self.list.song(self.list.playing))
        self.setFocus()
    
    def just_play(self):
        content = QMediaContent(QUrl.fromLocalFile(DEFAULT_SIGNAL_PATH))
        self.signal.setMedia(content)
        #self.signal.setVolume(int(volume))
        self.signal.play()
    
       
    def _play(self):
        self.play_signal()
        song = self.list.song(self.list.playing)
        self.state = PLAYING
        self.buttonPlay.setChecked(True)
        self.buttonPause.setChecked(False)
        song.buttonPlay.setIcon(self.PLAY_ICON)
        song.buttonPlay.setChecked(True)
        
        self.allow_automations_update()
        #mixer.music.play(start=self.start_pos / 1000)
        #mixer.music.pause()
        self.deck_L.setPosition(self.start_pos)
        self.start_playback_update()
        self.start_volume_update()
        self.deck_L.play()
        #mixer.music.unpause()
        print('PLAYING...', self.list.playing,  song.name)
        print('STATE:', self.deck_L.state())
           
    def _pause(self):
        song = self.list.song(self.list.playing)
        self.play_signal()
        self.start_pos += self.deck_L.position()
        self.deck_L.pause()
        #mixer.music.stop()
        self.state = PAUSED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(True)
        song.buttonPlay.setIcon(self.PAUSED_ICON)
        song.buttonPlay.setChecked(True)
        print('PAUSED...')
        print('STATE:', self.deck_L.state())
                
    def _stop(self, event=None):
        self.play_signal()
        print('_STOP -- ')
        #self.start_pos =  song.start_pos
        #mixer.music.stop()
        self.deck_L.stop()
        self.state = STOPED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(False)
        self.sliderPlaybackPos.setValue(0)
        song = self.list.song(self.list.playing)
        if song:
            song.buttonPlay.setIcon(self.PLAY_ICON)
            song.buttonPlay.setChecked(False)
            self.change_pos(song.start_pos)
        else:
            self.change_pos(0)
        print('STOPED...')
        print('STATE:', self.deck_L.state())
        
    def play_pause(self, event=None):
        if not self.enabled:
            print('Controls disabled!')
            return
        self.play_signal()
        print('sender:', self.sender())
        if self.sender():
            sender = self.sender().parent()
            if type(sender) == SongWidget:
                if sender !=  self.list.song(self.list.playing):
                    self._stop()
                    self.eject()
                    self.list.set_row(sender, playing=True)
                    self.load(sender)
            
        if self.state == STOPED:
            if self.list.song(self.list.playing) != self.list.song(self.list.selected):
                self.eject()
                self.list.set_row(self.list.selected, playing=True)
                self.load(self.list.song(self.list.selected))
            self._play()
            if self.sender() and self.sender() == self.buttonPause:
                self._pause()
        else:
            if self.state == PAUSED or not self.deck_L.state() == PLAYING:
                self._play()
            else:
                self._pause()
            
    def play_next(self, event=None):
        self.play_signal()
        self._stop()
        next_song = self.get_next_song()
        if next_song:
            self.eject()
            self.load(next_song)
            if self.sender() == self or self.options.checkBoxAutoplayFforw.isChecked():
                self._play()  
    
    def get_next_song(self):
        next_song = None
        if self.repeat_mode == REPEAT_ONE:
            print('repeat one')
            next_song =  self.list.song(self.list.playing)
        elif self.repeat_mode == PLAY_ALL or self.repeat_mode == REPEAT_ALL:
            print('play/repeat all')
            song = self.list.get_song('next')
            while song and song.muted:
                song = self.list.get_song('next')
            if song:
                next_song = song
            elif self.repeat_mode == REPEAT_ALL:
                self.list.playing = 0
                self.list.set_current_row(0)
                song = self.list.song(0)
                while song and song.muted:
                    song = self.list.get_song('next')
                next_song = song
        return next_song
    
    def play_previous(self, event=None):
        self.play_signal()
        self._stop()
        previous_song = self.list.get_song('previous')
        while previous_song and previous_song.muted:
            previous_song = self.list.get_song('previous')
        if previous_song:
            self.eject()   
            self.load(previous_song)
            if self.options.checkBoxAutoplayRew.isChecked():
                self._play()
    
    def deny_playback_automation(self): #Для отключения обновления слайдером
        self.allow_automations_update(playback=False, volume=None)
    
    def deny_volume_automation(self): #Для отключения обновления слайдером
        self.allow_automations_update(playback=None, volume=False)
            
    def allow_automations_update(self, playback=True, volume=True):
        if playback is not None:
            self.allow_playback_update = playback
        if volume is not None:
            self.allow_volume_update = volume
        
    def _update_playback_slider(self, song, current_pos, playback_pos, to_end_delta):
        print('UPDATE_PLAYBACK SLIDER --')
        while (self.state == PLAYING and#(mixer.music.get_busy() and 
               self.allow_playback_update and
               song ==  self.list.song(self.list.playing) and
               current_pos >= 0 and
               to_end_delta >= 0
               ):
            #current_pos = mixer.music.get_pos()
            current_pos = self.deck_L.position()
            playback_pos = self.start_pos + current_pos
            to_end_delta = song.end_pos - playback_pos
            if playback_pos % 250 < 20:
                self.sliderPlaybackPos.setValue(playback_pos)
            if playback_pos % 1000 < 20:
                current_min_sec, current_millisec = self.min_sec_from_ms(playback_pos, show_ms=True)
                self.labelCurrentPos.setText(current_min_sec)
                if self.high_acuracy:
                    self.labelCurrentPosMs.setText(current_millisec)
                else:
                    self.labelCurrentPosMs.hide()
            sleep(0.01)
        print('playback automation off')
        #self.deny_autopos()
        #print('mixer buzy:', mixer.music.get_busy())
        #print('allow update:', self.allow_playback_update)
        #print('current song:', song ==  self.list.song(self.list.playing))
        #print('current mixer pos', current_pos)
        #print('mixer pos:', mixer.music.get_pos())
        if ((current_pos < 0 or to_end_delta < 35) and  #Проверка перехода
                    self.state == PLAYING):
            self.allow_automations_update(volume=False)
            self.end_of_playback.emit()
    
    def _update_volume_automation(self, song, playback_pos):
        print('VOLUME AUTOMATION --')
        fade_volume = 0
        while (self.allow_volume_update and
                self.state == PLAYING):
            #current_pos = mixer.music.get_pos()
            current_pos = self.deck_L.position()
            playback_pos = self.start_pos + current_pos
            #to_end_delta = song.end_pos - playback_pos
            if playback_pos % 250 < 20:
                #self.sliderPlaybackPos.setValue(playback_pos)
                if song.faded:
                    fadein_raito, fadeout_raito = self.fade_raitos
                    fade_in, fade_out = song.fade_range
                    #print()
                    #print('in raito:', fadein_raito, 'out_raito', fadeout_raito)
                    #print('playback_pos:', playback_pos, 'in_pos', fade_in, 'out_pos:', fade_out)
                    if playback_pos < fade_in and fadein_raito:
                        fade_pos = abs(playback_pos - song.start_pos)
                        new_fade_volume = int(fade_pos * fadein_raito)
                        if new_fade_volume != fade_volume:    
                            fade_volume = new_fade_volume 
                            print('fade in! volume:', fade_volume)
                            self.sliderSongVol.setValue(fade_volume)
                    elif fade_volume != song.volume and playback_pos < fade_out:
                        self.sliderSongVol.setValue(song.volume)
                        fade_volume = song.volume
                    elif playback_pos > fade_out and fadeout_raito:
                        fade_pos = abs(playback_pos - song.end_pos)
                        new_fade_volume = int(fade_pos * fadeout_raito)
                        if new_fade_volume != fade_volume:    
                            fade_volume = new_fade_volume 
                            print('fade out! volume:', fade_volume)
                            self.sliderSongVol.setValue(fade_volume)
        print('volume automation off')
    
    def start_playback_update(self):
        # if self.playback_update_thread:
             #if self.playback_update_thread.is_alive():
                 #self.allow_automations_update(playback=False, volume=None)
        busy_count = 0
        if self.playback_update_thread:
            while self.playback_update_thread.is_alive():#not active_threads() < 2:
                print('playback_slider buzy!')
                sleep(0.01)
                busy_count += 1
                if busy_count > 20:
                    print('playback update force canceled')
                    self.allow_automations_update(playback=False, volume=None)
        song =  self.list.song(self.list.playing)
        #current_pos = mixer.music.get_pos()
        current_pos = self.deck_L.position()
        playback_pos = self.start_pos + current_pos #дублировано для проверки повтора
        to_end_delta = song.end_pos - playback_pos #дублировано для проверки перехода
        print('START PLAYBACK SLIDER')
        self.allow_automations_update(playback=True, volume=None)
        print('START PLAYBACK SLIDER: allow update: playback-', self.allow_playback_update, 'volume-', self.allow_volume_update)
        self.playback_update_thread = Thread(target=self._update_playback_slider,
               args=(song, current_pos, playback_pos, to_end_delta))
        self.playback_update_thread.start()
    
    def start_volume_update(self):
        if self.volume_update_thread:
            if self.volume_update_thread.is_alive():
                self.allow_automations_update(playback=None, volume=False)
        song =  self.list.song(self.list.playing)
        #current_pos = mixer.music.get_pos()
        current_pos = self.deck_L.position()
        playback_pos = self.start_pos + current_pos #дублировано для проверки повтора
        #to_end_delta = song.end_pos - playback_pos #дублировано для проверки перехода
        print('START VOLUME AUTOMATION')
        self.allow_automations_update(playback=None, volume=True)
        self.volume_update_thread = Thread(target=self._update_volume_automation,
               args=(song, playback_pos))
        self.volume_update_thread.start()
                       
    def change_pos(self, pos=None):
        print('CHANGE_POS --')
        #print('pos:', pos)
        if pos == None:
            slider_pos = self.sliderPlaybackPos.value()
        else:
            slider_pos = pos
        start_pos, end_pos = self.sliderPlaybackRange.value()
        if slider_pos < start_pos:
            slider_pos = start_pos
        elif slider_pos > end_pos:
            slider_pos = end_pos
        self.start_pos = slider_pos
        self.sliderPlaybackPos.setValue(slider_pos)
        if self.state == PLAYING:#mixer.music.get_busy():
            print('CHANGE_POS: Playing mode - start playing and playback update')
            #mixer.music.stop().    ##### ОТКЛЮЧЕНО ЭКСПЕРИМЕНТАЛЬНО. Вырубалось обновление слайдера в этот момент
            self.deck_L.setPosition(slider_pos)
            self.deck_L.play()
            #mixer.music.play(start=slider_pos / 1000)
            self.start_playback_update()
        if not self.allow_playback_update:  ### предполижительно из-за доступа к переменной вырубалось обновление слайдера
            self.allow_automations_update(playback=True, volume=None)
        current_min_sec, current_millisec = self.min_sec_from_ms(slider_pos, show_ms=True)
        self.labelCurrentPos.setText(current_min_sec)
        if self.high_acuracy:
            self.labelCurrentPosMs.show()
            self.labelCurrentPosMs.setText(current_millisec)
            self.high_acuracy = False
        print('CHANGE_POS: changed to', self.start_pos) 
    
    def change_range(self, pbrange=None):
        song = self.list.song(self.list.playing)
        fade_in, fade_out = song.fade_range
        if not pbrange:  #slider released
            start_pos, end_pos = self.sliderPlaybackRange.value()
            self.list.set_saved(False)
        else:       #button set range
            start_pos, end_pos = pbrange
            self.sliderPlaybackRange.setValue(pbrange)
        fade_in_delta = fade_in - song.start_pos
        fade_out_delta = fade_out - song.end_pos
        #song.start_pos = start_pos
        #song.end_pos = end_pos
        song.set_playback_range((start_pos, end_pos))
        self.labelEndPos.setText(self.min_sec_from_ms(end_pos))
        if self.sliderPlaybackPos.value() < start_pos:
            self.change_pos(start_pos)
        elif self.sliderPlaybackPos.value() > end_pos:
            self.change_pos(end_pos)
        if fade_in_delta:
            fade_in = song.start_pos + fade_in_delta
        if fade_out_delta:
            fade_out = song.end_pos + fade_out_delta
        self.change_fade_range((fade_in, fade_out))
    
    def set_range(self):
        start_pos, end_pos = self.sliderPlaybackRange.value()
        if self.sender() == self.buttonSetStart:
            start_pos = self.sliderPlaybackPos.value()
        elif self.sender() == self.buttonSetEnd:
            end_pos = self.sliderPlaybackPos.value()
        self.sliderPlaybackRange.setValue((start_pos, end_pos))
        self.change_range((start_pos, end_pos))    
        
    def step_rewind(self):
        new_slider_pos = self.sliderPlaybackPos.value() - CHANGE_POS_STEP
        if new_slider_pos >= 0:
            self.high_acuracy = True
            self.deny_playback_automation()
            #self.sliderPlaybackPos.setValue(new_slider_pos)
            self.change_pos(new_slider_pos)
        
    def step_fforward(self):
        new_slider_pos = self.sliderPlaybackPos.value() + CHANGE_POS_STEP
        if new_slider_pos <=  self.list.song(self.list.playing).length:
            self.high_acuracy = True
            self.deny_playback_automation()
            #self.sliderPlaybackPos.setValue(new_slider_pos)
            self.change_pos(new_slider_pos)
    
    def load(self, song):
        print('LOAD')
        if song:
            if not song.muted:
                print('loaded: ', song.name[:20])
                #print('start pos:', song.start_pos)
                song.buttonDelete.setEnabled(True)
                self.enable(just_playback=True)
                #self.buttonPlay.setEnabled(True)
                #self.buttonPause.setEnabled(True)
                #self.buttonStop.setEnabled(True)
                if song.repeat:
                    self.switch_repeat_to(REPEAT_ONE)
                self.sliderPlaybackPos.setMaximum(song.length)
                self.sliderPlaybackRange.setMaximum(song.length)
                self.sliderFadeRange.setMaximum(song.length)
                #self.sliderPlaybackRange.setValue((song.start_pos, song.end_pos))
                #self.list.set_row(song, playing=True) #раскомментировано для загрузки песни при нажатии stop: перенесено в stop
                #pdb.set_trace()
                self.change_range((song.start_pos, song.end_pos))
                #self.song_vol_change(song.volume, move_slider=True)
                self.sliderSongVol.setValue(song.volume)
                if song.faded or song.range_limited or self.options.checkBoxShowAutomations.isChecked():
                    self.show_automations()
                    if self.fade_raitos[0]:
                        self.sliderSongVol.setValue(0)
                #self.change_fade_range(song.fade_range)
                self.start_pos = song.start_pos
                #self.change_pos(self.start_pos) #change_pos вызывается из change_range, если playback_pos < start_pos
                content = QMediaContent(QUrl.fromLocalFile(song.path))
                self.deck_L.setMedia(content)
            else:
                print('song not loaded because it is muted') 
            self.waveform = song.waveform
            self.resizeEvent(QtGui.QResizeEvent)
        else:
             print('song not loaded. No song to load! Current song:', self.list.song(self.list.selected))
    
    def eject(self):
        song = self.list.song(self.list.playing)
        if song:
            song.normal_mode()
            song.buttonPlay.setIcon(self.PLAY_ICON)
            song.buttonPlay.setChecked(False)
        self.show_automations(False)
        self.enable(False, just_playback=True)
        self.waveform = []
        #mixer.music.unload()
                    
    def min_sec_from_ms(self, milliseconds, show_ms=False):
        sec_float = milliseconds / 1000
        sec_int = int(sec_float)
        hundr_sec = int((sec_float - sec_int) * 100)
        minutes = sec_int // 60
        sec = sec_int % 60
        if show_ms:
            result = (f'{minutes :02.0f}:{sec :02.0f}', f'{hundr_sec :03.0f}')
        else:
            self.high_acuracy = False
            result = f'{minutes :02.0f}:{sec :02.0f}'
        return result
    
    def set_repeat(self):
        #selected_song = self.list.song(listSongs.selected)
        if self.sender() == self.buttonRepeat:
            self.list.set_saved(False)
            self.repeat_mode = (self.repeat_mode + 1) % 4
            self.prev_repeat_mode = self.repeat_mode
            if self.repeat_mode == PLAY_ONE:
                self.list.song(self.list.playing).repeat = False
                self.list.song(self.list.playing).buttonRepeat.setChecked(False)
                self.switch_repeat_to(PLAY_ONE)
            elif self.repeat_mode == REPEAT_ONE:
                self.list.song(self.list.playing).repeat = True
                self.list.song(self.list.playing).buttonRepeat.setChecked(True)
                self.switch_repeat_to(REPEAT_ONE)
            elif self.repeat_mode == PLAY_ALL:
                self.list.song(self.list.playing).repeat = False
                self.list.song(self.list.playing).buttonRepeat.setChecked(False)
                self.switch_repeat_to(PLAY_ALL)
            elif self.repeat_mode == REPEAT_ALL:
                self.list.song(self.list.playing).repeat = False
                self.list.song(self.list.playing).buttonRepeat.setChecked(False)
                self.switch_repeat_to(REPEAT_ALL)
        else:
            repeated_song = self.sender().parent()
            repeated_song.repeat = not repeated_song.repeat
            repeated_song.buttonRepeat.setChecked(repeated_song.repeat)
            if repeated_song ==  self.list.song(self.list.playing):
                if repeated_song.repeat:
                    self.switch_repeat_to(REPEAT_ONE)
                else:
                    self.switch_repeat_to(self.prev_repeat_mode)
            self.list.set_saved(False)
    
    def switch_repeat_to(self, mode):
        mode_settings = self.REPEAT_MODES.get(mode)
        self.repeat_mode = mode
        self.buttonRepeat.setChecked(mode_settings.get('checked'))
        self.buttonRepeat.setIcon(mode_settings.get('icon'))
    
    def master_vol_change(self, vol):
        self.master_volume = vol
        self.sliderMasterVol.setValue(self.master_volume)
        self.apply_volume()
            
    def song_vol_change(self, vol, move_slider=False):
        print('SONG VOLUME CHANGE: changed to', vol)
        if move_slider: #слайдер вызывает этот же метод при перемещении, если его позиция изменилась
            self.sliderSongVol.setValue(self.song_volume)
        self.song_volume = vol
        self.apply_volume()
        
    def song_vol_write(self,):
        print('song vol writed:', self.song_volume)
        self.list.song(self.list.playing).volume = self.song_volume
        if self.state == PLAYING:
            self.start_volume_update()
            
    def apply_volume(self):
        mixer_volume = (self.song_volume * self.master_volume) / 100
        self.deck_L.setVolume(mixer_volume)
        #mixer.music.set_volume(mixer_volume)
    
    def vol_up(self, event=None):
        next_master_volume = self.master_volume + self.VOLUME_STEP
        if next_master_volume > self.MAX_VOL:
            self.master_vol_change(self.MAX_VOL)
            print('MAX VOLUME!')
        else:
            self.master_vol_change(next_master_volume)
        print('VOLUME:', self.master_volume)
        
    def vol_down(self, event=None):
        next_master_volume = self.master_volume - self.VOLUME_STEP
        if next_master_volume < self.MIN_VOL:
            self.master_vol_change(self.MIN_VOL)
            print('MIN VOLUME!')
        else:
            self.master_vol_change(next_master_volume)
        print('VOLUME:', self.master_volume)
    
    def change_fade_range(self, fade_range=None):
        song = self.list.song(self.list.playing)
        if not fade_range:     #slider released
            fadein_pos, fadeout_pos = self.sliderFadeRange.value()
            self.list.set_saved(False)
        else:               #set_fade_range
            fadein_pos, fadeout_pos = fade_range
        song.set_fading((fadein_pos, fadeout_pos))
        self.sliderFadeRange.setValue(song.fade_range)
        self.fade_raitos = self.get_fade_raitos()
    
    def set_fade_range(self):
        fadein_pos, fadeout_pos = self.sliderFadeRange.value()
        playback_pos = self.sliderPlaybackPos.value()
        if self.sender() == self.buttonSetFadeIn:
            fadein_pos = playback_pos
            if fadein_pos > fadeout_pos:
                fadein_pos = fadeout_pos
        elif self.sender() == self.buttonSetFadeOut:
            fadeout_pos = playback_pos
            if fadeout_pos < fadein_pos:
                fadeout_pos = fadein_pos
        self.sliderFadeRange.setValue((fadein_pos, fadeout_pos))
        self.change_fade_range((fadein_pos, fadeout_pos))
        
    def get_fade_raitos(self):
        song = self.list.song(self.list.playing)
        fade_in, fade_out = song.fade_range
        fade_in, fade_out = fade_in - song.start_pos, song.end_pos - fade_out
        print('GET FADE RAITOS --')
        print('fade in:', fade_in, 'fade out', fade_out, 'volume:', song.volume)
        if fade_in:
            fade_in_raito = song.volume / fade_in
        else:
            fade_in_raito = 0
        if fade_out:
            fade_out_raito = song.volume / fade_out
        else:
            fade_out_raito = 0
        print('raitos:', fade_in_raito, fade_out_raito)
        return (fade_in_raito, fade_out_raito)
        
    def show_automations(self, show=True):
        if show:
            self.buttonAutomations.setChecked(True)
            self.buttonSetStart.show()
            self.sliderPlaybackRange.show()
            self.buttonSetEnd.show()
            self.buttonSetFadeIn.show()
            self.sliderFadeRange.show()
            self.buttonSetFadeOut.show()
        else:
            self.buttonAutomations.setChecked(False)
            self.buttonSetStart.hide()
            self.sliderPlaybackRange.hide()
            self.buttonSetEnd.hide()
            self.buttonSetFadeIn.hide()
            self.sliderFadeRange.hide()
            self.buttonSetFadeOut.hide()
               
    def reset_song_settings(self):
        self.master_vol_change(50)
        self.song_vol_change(100, move_slider=True)
        self.change_range((0,  self.list.song(self.list.playing).length))
        self.change_fade_range((0,  self.list.song(self.list.playing).length))
        self.list.song(self.list.playing).repeat = False
        self.list.song(self.list.playing).muted = False
        self._stop()
    
    def enable(self, state=True, just_playback=False):
        print('ENABLE:', state)
        self.enabled = state
        self.buttonStop.setEnabled(state)
        self.buttonPlay.setEnabled(state)
        self.buttonPause.setEnabled(state)
        self.enable_controls(state)
        if not just_playback:
            self.buttonPrevious.setEnabled(state)
            self.buttonNext.setEnabled(state)
            self.buttonRepeat.setEnabled(state)
            self.buttonReset.setEnabled(state)
            self.sliderMasterVol.setEnabled(state)
            self.sliderSongVol.setEnabled(state)
            self.sliderFadeRange.setEnabled(state)
            self.sliderPlaybackPos.setEnabled(state)
            self.sliderPlaybackRange.setEnabled(state)
            self.buttonSetStart.setEnabled(state)
            self.buttonSetEnd.setEnabled(state)
            self.buttonSetFadeIn.setEnabled(state)
            self.buttonSetFadeOut.setEnabled(state)
            self.buttonAutomations.setEnabled(state)
    
    def play_signal(self, enabled=None, volume=None):
        if enabled == None:
            enabled = self.options.checkBoxEnableSignals.isChecked()
        if volume == None:
            volume = self.options.signals_volume
        if enabled:
            print(volume)
            self.signal.setVolume(int(volume))
            self.signal.play()
    
    def enable_controls(self, setting=True):
        self.controls_enabled = setting
    
    def enable_presentation_mode(self, enable=True):
        self.presentation_mode = enable
        if enable:
            self.buttonPresentationMode.setChecked(True)
            self.on_press_hook = keyboard.on_press(self.presentation_controls)
            self.tab_shortcut.setEnabled(False)
        else:
            self.buttonPresentationMode.setChecked(False)
            print('PRES MODE OFF')
            keyboard.unhook(self.on_press_hook)
            self.tab_shortcut.setEnabled(True)
            self.setFocus()
                    
    def keyPressEvent(self, event):
        print('KEY PRESS')
        print('player.enabled:', self.enabled)
        print('controls enabled:', self.controls_enabled)
        if (not self.presentation_mode and 
                self.options.checkBoxKeyControlsEnable.isChecked() and
                self.enabled
                ):
            print(event.key())
            action = self.controls.get(event.key())
            if action and self.controls_enabled:
                action()
            
    def presentation_controls(self, event):
        print(event.name)
        if event.name == 'up':
            self.play_previous()
        elif event.name == 'down':
            self.play_next()
        elif event.name == 'tab':
            self.play_pause()
                
    def closeEvent(self, event):
        self.options.save()
        self.deny_playback_automation()
        self.deny_volume_automation()
        self.deck_L.stop()
        #mixer.music.unload()
        event.accept()
    
    def resizeEvent(self, event):
        slider_width = self.width() - PLAYBACK_SLIDER_WIDTH_OFFSET - PLAYBACK_SLIDER_WAVEFORM_OFFSET
        song = self.list.song(self.list.playing)
        if song:
            base_waveform = song.waveform
            #print('current waveform len:', len(self.waveform))
            #print('slider width:', slider_width)
            new_waveform = []
            step = len(base_waveform) / slider_width
            read_pos = 0
            while read_pos < len(base_waveform) - 1:
                new_waveform.append(base_waveform[int(read_pos)])
                read_pos += step
            #print('new waveform len:', len(new_waveform))
            self.waveform = new_waveform
        
    def paintEvent(self, event) -> None:  #a0: QtGui.QPaintEvent
        painter = QtGui.QPainter(self)
        painter.setBrush(QtCore.Qt.lightGray)
        pos = self.sliderPlaybackPos.pos()
        rect = self.sliderPlaybackPos.rect()
        margin_x = 4
        margin_y = 5
        #print(pos.x(), pos.y(), rect.width(), rect.height())
        polygon = QtGui.QPolygon()
        polygon.append(QtCore.QPoint(pos.x() + margin_x, 
                                     pos.y() + rect.height() - margin_y))
        for i, sample in enumerate(self.waveform):
            polygon.append(QtCore.QPoint(pos.x() + margin_x + i,
                                         pos.y() + rect.height() - margin_y - sample))
        polygon.append(QtCore.QPoint(pos.x() + margin_x + len(self.waveform), 
                                     pos.y() + rect.height() - margin_y))
        painter.drawConvexPolygon(polygon) # рисует ту же линию, но с затониорованым низом.
        #painter.drawPolyline(polygon) # может сделать пункт настроек?
    
    def qlist_info(self):
        print('INFO:')
        print('current_track_num:', self.list.playing)
        for index, song in enumerate(self.list.list.get_all_songs()):
            name = 'NONE'
            if song:
                name = song.name
            print(index, name)
        print('Controls enabled:', self.controls_enabled)
        print('Presentation mode:', self.presentation_mode)


def main():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    app.setWindowIcon(QtGui.QIcon(os.path.join(BASE_DIR, 'app_icon.icns')))
    window = ClickerPlayerApp() 
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение
    exit()

if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()