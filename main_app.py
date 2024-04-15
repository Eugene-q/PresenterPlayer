# -*- coding: utf-8 -*-
'''master VERSION'''


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
from PyQt5.QtCore import QUrl, QCoreApplication
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QAudioDecoder
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

DEFAULT_PLAYBACK_DIR = os.path.join(USER_MUSIC_DIR, 'song_lists/new_songlist_music')
DEFAULT_SAVE_DIR = os.path.join(USER_MUSIC_DIR, 'song_lists')
SONG_LIST_EXTENSION = '.sl'
SUPPORTED_FILE_TYPES = '.mp3', '.wav', '.m4a', '.mpeg'
DEFAULT_SONGLIST_NAME = 'New_songlist'
DEFAULT_SONG_BUTTONS_SIZE = 20
DEFAULT_SONG_FONT = 'Arial'
DEFAULT_SONG_FONT_SIZE = 20
DEFAULT_SONG_BUTTONS_SET = {'play': True, 'duplicate': True,
                            'repeat': True, 'mute': True, 'delete': True}

OPTIONS_FILE_PATH = os.path.join(BASE_DIR, 'assets/options.json')
DEFAULT_OPTIONS = {'last_playlist_path': os.path.join(DEFAULT_SAVE_DIR, 
                                            DEFAULT_SONGLIST_NAME + SONG_LIST_EXTENSION),
                   'signals_enabled': False,
                   'signals_volume': 50,
                   'always_show_automations': False,
                   'autoplay_fforw': False,
                   'autoplay_rew': False,
                   'clicker_enabled_in_list_mode': True,
                   'change_pos_step': 250,
                   'rename_delete_old_list': False,
                   'default_music_dir': USER_MUSIC_DIR,
                   'default_save_dir': DEFAULT_SAVE_DIR,
                   'song_buttons_size': DEFAULT_SONG_BUTTONS_SIZE,
                   'song_font_size': DEFAULT_SONG_FONT_SIZE,
                   'song_buttons_set': DEFAULT_SONG_BUTTONS_SET,
                   'show_song_number': False,
                   'show_waveform': True,
                }
# repeat modes
PLAY_ALL = 0
REPEAT_ALL = 1
PLAY_ONE = 2
AS_LIST = 3
REPEAT_ONE = 4

FOLDER_NOT_FOUND_WARNING = 'Не удалось найти папку с файлами песен!'
SONGFILE_NOT_FOUND_WARNING = 'Не удалось найти файл\n{}'
WRONG_FILE_NAME_WARNING = '''Вы искали файл\n{}\nно указали файл с другим именем\n{}\nВсё правильно?\n
При добавлении в папку списка файл будет переименован'''
LIST_FILE_EXISTS_WARNING = 'Список с именем {} уже есть!\nВсё его содержимое будет перезаписано!'
CLEAR_WARNING = 'Удалить все песни из списка? \nФайлы песен останутся папке списка.'
DELETE_PLAYING_WARNING = 'Нельзя удалить то, что сейчас играет!'
SOURCE_DELETE_WARNING = '''Песни {} больше нет в списке, но файл с ней ещё остался.
Удалить файл или оставить в папке списка?'''
LIST_DELETE_WARNING = 'Полностью удалить список и связанные с ним файлы?'
RESET_SONG_SETTINGS_WARNING = 'Настройки громкости и позиции будут сброшены!'

STOPED = 0
PLAYING = 1
PAUSED = 2

OK = 0
MIDDLE = 1
CANCEL = 2
OK_CHECKED = 3
MIDDLE_CHECKED = 4
CANCEL_CHECKED = 5

DEFAULT_MASTER_VOLUME = 50
DEFAULT_SONG_VOLUME = 100

BASE_WAVEFORM_DISPLAY_WIDTH = 1920
PLAYBACK_SLIDER_WIDTH_OFFSET = 92
PLAYBACK_SLIDER_WAVEFORM_OFFSET = 19#10
PLAYBACK_SLIDER_HEIGHT = 30
WAVEFORM_HEIGHT = 70
WAVEFORM_AVERAGING_FRAME_WIDTH = 15


class OptionsDialog(QtWidgets.QDialog):
    def __init__(self, options_file_path, player):
        super().__init__()
        
        uic.loadUi(OPTIONS_DIALOG_UI_PATH, self)

        self.options_file_path = options_file_path
        self.player = player
        
        self.sliderSignalsVol.sliderReleased.connect(self.test_signal_vol)
        self.buttonSetDefaultSaveDir.clicked.connect(
                            lambda: self.set_default_dir(self.lineDefaultSaveDir))
        self.buttonSetDefaultMusicDir.clicked.connect(
                            lambda: self.set_default_dir(self.lineDefaultMusicDir))
                            
        self.test_song_widget = SongWidget(parent=self, id=None, path='', name='Название песни', length=0)
        self.test_song_widget.buttonDuplicate.setCheckable(True)
        self.test_song_widget.buttonDelete.setCheckable(True)
        
        self.layoutSongListWidget.addWidget(self.test_song_widget)
        self.spinBoxFontSize.valueChanged.connect(self.test_song_widget.update_font)
        self.spinBoxButtonsSize.valueChanged.connect(self.test_song_widget.update_buttons_size)
        self.buttonSave.clicked.connect(self.save)
        self.buttonCancel.clicked.connect(self.cancel)
        
        self.load()
        self.cancel()
    
    def load(self):
        if os.path.exists(self.options_file_path):
            with open(self.options_file_path, 'r', encoding='utf-8') as options_file:
                options_set = json.load(options_file) or DEFAULT_OPTIONS
        else:
            options_set = DEFAULT_OPTIONS
        self.last_playlist_path = options_set.get('last_playlist_path')
        self.beeps_volume = options_set.get('signals_volume')
        self.checkBoxEnableSignals.setChecked(options_set.get('signals_enabled'))
        self.checkBoxShowAutomations.setChecked(options_set.get('always_show_automations'))
        self.checkBoxShowWaveform.setChecked(options_set.get('show_waveform'))
        self.checkBoxAutoplayFforw.setChecked(options_set.get('autoplay_fforw'))
        self.checkBoxAutoplayRew.setChecked(options_set.get('autoplay_rew'))
        self.checkBoxKeyControlsEnable.setChecked(options_set.get('clicker_enabled_in_list_mode'))
        self.spinBoxChangePosStep.setValue(options_set.get('change_pos_step'))
        self.checkBoxRenameDeleteOldList.setChecked(options_set.get('rename_delete_old_list'))
        self.lineDefaultMusicDir.setText(options_set.get('default_music_dir'))
        self.lineDefaultSaveDir.setText(options_set.get('default_save_dir'))
        self.spinBoxButtonsSize.setValue(options_set.get('song_buttons_size'))
        self.spinBoxFontSize.setValue(options_set.get('song_font_size'))
        song_buttons = options_set.get('song_buttons_set')
        self.test_song_widget.buttonPlay.setChecked(song_buttons.get('play'))
        self.test_song_widget.buttonDuplicate.setChecked(song_buttons.get('duplicate'))
        self.test_song_widget.buttonRepeat.setChecked(song_buttons.get('repeat'))
        self.test_song_widget.buttonMute.setChecked(song_buttons.get('mute'))
        self.test_song_widget.buttonDelete.setChecked(song_buttons.get('delete'))
        self.test_song_widget.buttonNumber.setChecked(options_set.get('show_song_number'))

    def save(self):
        self.last_playlist_path = self.player.list.save_file_path
        self.beeps_volume = self.sliderSignalsVol.value()
        options_set = {'last_playlist_path': self.last_playlist_path,
                       'signals_volume': self.beeps_volume,
                       'signals_enabled': self.checkBoxEnableSignals.isChecked(),
                       'always_show_automations': self.checkBoxShowAutomations.isChecked(),
                       'show_waveform': self.checkBoxShowWaveform.isChecked(),
                       'autoplay_fforw': self.checkBoxAutoplayFforw.isChecked(),
                       'autoplay_rew': self.checkBoxAutoplayRew.isChecked(),
                       'clicker_enabled_in_list_mode': self.checkBoxKeyControlsEnable.isChecked(),
                       'change_pos_step': self.spinBoxChangePosStep.value(),
                       'rename_delete_old_list': self.checkBoxRenameDeleteOldList.isChecked(),
                       'default_music_dir': self.lineDefaultMusicDir.text(),
                       'default_save_dir': self.lineDefaultSaveDir.text(),
                       'song_buttons_size': self.spinBoxButtonsSize.value(),
                       'song_font_size': self.spinBoxFontSize.value(),
                       'song_buttons_set': self.get_song_buttons_set(),
                       'show_song_number': self.test_song_widget.buttonNumber.isChecked()
                   }
        with open(self.options_file_path, 'w', encoding='utf-8') as options_file:
            json.dump(options_set, options_file, indent=4)
        self.player.show_automations(self.checkBoxShowAutomations.isChecked())
        self.player.list.list.update_items(font_size=self.spinBoxFontSize.value(),
                                        buttons_size=self.spinBoxButtonsSize.value(),
                                        buttons_set=self.get_song_buttons_set().values())
        if self.checkBoxShowWaveform.isChecked():
            self.player.resize_waveform()
        self.player.setFocus()
        self.hide()
        
    def cancel(self):
        self.sliderSignalsVol.setValue(int(self.beeps_volume))
        self.checkBoxEnableSignals.setChecked(self.checkBoxEnableSignals.isChecked())
        self.player.setFocus()
        self.hide()
    
    def test_signal_vol(self,):
        if self.checkBoxEnableSignals.isChecked():
            volume = self.sliderSignalsVol.value()
            self.player.play_beep(enabled=True, 
                                    volume=volume)
                                    
    def set_default_dir(self, dir_line):
        dir_ = QtWidgets.QFileDialog.getExistingDirectory(self,
                                        'Выбрать папку',
                                        dir_line.text())
        if dir_:
            dir_line.setText(dir_)
            
    def save_dir(self):
        return self.lineDefaultSaveDir.text()
        
    def get_song_buttons_set(self):
        return {'play': self.test_song_widget.buttonPlay.isChecked(),
                'duplicate': self.test_song_widget.buttonDuplicate.isChecked(),
                'repeat': self.test_song_widget.buttonRepeat.isChecked(),
                'mute': self.test_song_widget.buttonMute.isChecked(),
                'delete': self.test_song_widget.buttonDelete.isChecked(),
                }
    

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
                       repeat_mode=AS_LIST,
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
        self.repeat_mode = repeat_mode
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

        self.REPEAT_ONE_ICON = QtGui.QIcon(QtGui.QPixmap(':/song/icons/repeat_song.png'))
        self.PLAY_ONE_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/dont_repeat_one.png'))
        self.REPEAT_MODES = {AS_LIST: {'checked': False, 'icon':  self.REPEAT_ONE_ICON},
                             REPEAT_ONE: {'checked': True,'icon':  self.REPEAT_ONE_ICON},
                             PLAY_ONE: {'checked': True, 'icon':  self.PLAY_ONE_ICON}
                         }
        if id != None:
            self.buttonPlay.clicked.connect(self.play)
            self.buttonMute.clicked.connect(self.mute)
            self.buttonMute.setChecked(self.muted)
            self.buttonRepeat.clicked.connect(self.set_repeat)
            self.buttonDuplicate.clicked.connect(self.duplicate)
            self.buttonDelete.clicked.connect(self.delete_from_list)
            self.buttonNumber.hide()
            self.set_repeat_to(self.repeat_mode)
        else:
            self.labelNumber.hide()
        
        self.labelSongName.setText(name)
        self.labelSongName.setToolTip(name)
        self.labelSongName.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.labelSongName.customContextMenuRequested.connect(self.show_context_menu)
        self.lineNewSongName.returnPressed.connect(self.save_name)
        self.lineNewSongName.hide()
        #print('song created. fade range:', self.fade_range)
    
    def show_context_menu(self, p):
        if (self.song_list.song(self.song_list.playing) == self and
                            self.song_list.player.state == PLAYING):
            play_action = 'Пауза'
        else:
            play_action = 'Играть'
        if self.muted:
            mute_action = 'Включить'
        else:
            mute_action = 'Выключить'
        if self.repeat_mode == PLAY_ONE:
            repeat_action = 'Не повторять'
        elif self.repeat_mode == AS_LIST:
            repeat_action = 'Повторять'
        elif self.repeat_mode == REPEAT_ONE:
            repeat_action = 'Доиграть и стоп'
        actions = ((play_action, self.play), 
                   ('Дублировать', self.duplicate),
                   (repeat_action, self.set_repeat),
                   (mute_action, self.mute),
                   ('Удалить', self.delete_from_list),
                   )
        buttons_set = self.song_list.options.get_song_buttons_set().values()
        menu = QtWidgets.QMenu(self)
        for button, action in zip(buttons_set, actions):
            if not button:
                menu_item, action = action
                if menu_item == play_action and self.muted:
                    continue
                menu.addAction(self.tr(menu_item), action)
        if not menu.isEmpty():
            menu.exec_(QtGui.QCursor.pos())
    
    def play(self):
        self.song_list.player.play_pause(song=self)
        
    def mute(self):
        self.muted = not self.muted
        self.buttonMute.setChecked(self.muted)
        self.song_list.mute_song(self)
        
    def duplicate(self):
        self.song_list.duplicate_song_widget(self)
        
    def delete_from_list(self):
        self.song_list.delete_song_widget(self)
        
    def set_repeat(self):
        self.repeat_mode = (self.repeat_mode - 1) % 3 + 2
        if self.song_list.player.repeat_mode == PLAY_ONE and self.repeat_mode == AS_LIST:
            self.repeat_mode = (self.repeat_mode - 1) % 3 + 2
        print('Repeat mode sets...', self.repeat_mode)
        self.set_repeat_to(self.repeat_mode)
        
    def set_repeat_to(self, mode):
        print('SONG SET REPEAT TO', mode)
        mode_settings = self.REPEAT_MODES.get(mode)
        self.repeat_mode = mode
        self.buttonRepeat.setChecked(mode_settings.get('checked'))
        self.buttonRepeat.setIcon(mode_settings.get('icon'))
        
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
        self.update_filename()
        self.song_list.save()
        self.normal_mode()
        
    def normal_mode(self):
        self.lineNewSongName.clearFocus()
        self.lineNewSongName.hide()
        self.labelSongName.show()
        self.song_list.player.enable_controls()
    
    def update_filename(self):
        filedir, filename = os.path.split(self.path)
        old_name, filetype = os.path.splitext(filename)
        if old_name != self.name:
            new_path = os.path.join(filedir, self.name + filetype)
            copyfile(self.path, new_path)
            os.remove(self.path)
            self.path = new_path
    
    def update_buttons_size(self, value):
        self.buttonPlay.setFixedSize(value, value)
        self.buttonPlay.setIconSize(QtCore.QSize(value, value))
        self.buttonRepeat.setFixedSize(value, value)
        self.buttonRepeat.setIconSize(QtCore.QSize(value, value))
        self.buttonDelete.setFixedSize(value, value)
        self.buttonDelete.setIconSize(QtCore.QSize(value, value))
        self.buttonMute.setFixedSize(value, value)
        self.buttonMute.setIconSize(QtCore.QSize(value, value))
        self.buttonDuplicate.setFixedSize(value, value)
        self.buttonDuplicate.setIconSize(QtCore.QSize(value, value))
        self.buttonNumber.setFixedSize(value, value)
    
    def update_buttons_set(self, buttons_set):
        buttons = (self.buttonPlay, 
                   self.buttonDuplicate,
                   self.buttonRepeat,
                   self.buttonMute,
                   self.buttonDelete
                   )
        for button, is_on in zip(buttons, buttons_set):
            if is_on:
                button.show()
            else:
                button.hide()
    
    def update_font(self, size=DEFAULT_SONG_FONT_SIZE):
        self.labelNumber.setFont(QtGui.QFont(DEFAULT_SONG_FONT, size))
        self.labelSongName.setFont(QtGui.QFont(DEFAULT_SONG_FONT, size))
        self.lineNewSongName.setFont(QtGui.QFont(DEFAULT_SONG_FONT, size))
                
    def update_number(self, number):
        if self.song_list.options.test_song_widget.buttonNumber.isChecked():
            self.labelNumber.setText(f' {str(number)} - ')
            self.labelNumber.show()
        else:
            self.labelNumber.hide()
    
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
    
    def set_waveform(self, waveform):
        self.waveform = waveform


class SongListWidget(QtWidgets.QWidget):
    def __init__(self, player, options):
        super().__init__()
        
        #GUI settings
        uic.loadUi(SONG_LIST_UI_PATH, self) #стало вылезать Python: PID 52560: Invalid argument. Ни на что не влияет
        self.list = SongList(self)
        self.layoutSongList.addWidget(self.list)
        self.layoutSongList.layoutBottomMargin = 0
        
        self.lineListHeader.hide()
        self.lineListHeader.returnPressed.connect(self.save_list_name)
        self.buttonListHeader.clicked.connect(self.rename_mode)
        self.buttonListHeader.setToolTip(self.buttonListHeader.text())
        self.buttonListHeader.setStyleSheet("text-align:left;")
        self.buttonAddTrack.clicked.connect(self.add_songs)
        self.buttonNewList.clicked.connect(self.new_list)
        self.buttonSaveListAs.clicked.connect(self.save_as)
        self.buttonLoadList.clicked.connect(self.load)
        self.buttonClearList.clicked.connect(self.clear)
        self.buttonDeleteList.clicked.connect(self.delete)
        
        self.options = options
        self.player = player
        self.new_list_created = False
        self.renamed_song = None
        self.id_source = 0
        self.save_file_path = ''
        self.playback_dir = DEFAULT_PLAYBACK_DIR
        if not os.path.exists(self.options.save_dir()):
            os.mkdir(self.options.save_dir())
        self.selected = 0               #selected song index
        self.playing = self.selected    #playing song index
        self.set_current_row(0)
    
    def scale_number(self, unscaled, to_min, to_max, from_min, from_max):
        return (to_max-to_min)*(unscaled-from_min)/(from_max-from_min)+to_min
       
    def add_songs(self, filenames=[], songs_info=[]): 
        list_was_empty = self.is_empty() 
        if songs_info:                   # Добавление песен из загруженного списка
            for info in songs_info:
                song_path = os.path.join(self.playback_dir, info.get('name')+info.get('file_type'))
                song_widget = SongWidget(parent=self,
                                        id=info.get('id'),
                                        path=song_path,
                                        name=info.get('name'),
                                        file_type=info.get('file_type'),
                                        volume=info.get('volume'),
                                        length=info.get('length'),
                                        start_pos=info.get('start_pos'),
                                        end_pos=info.get('end_pos'),
                                        repeat_mode=info.get('repeat_mode'),
                                        fade_range=info.get('fade_range'),
                                        muted=info.get('muted'),
                                        waveform=info.get('waveform')
                                        )
                self.add_song_widget(song_widget)
        else:
            if not filenames:           # Добавление песен по кнопке +
                supported_file_types = ' *'.join(SUPPORTED_FILE_TYPES)
                filepaths = QtWidgets.QFileDialog.getOpenFileNames(self, 
                                                        'Добавить дорожки', 
                                                        self.options.lineDefaultMusicDir.text(), 
                                                        F'Music Files (*{supported_file_types})',
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
                                       # TODO Окно предупреждения об удалении недопустимых символов
                    filenames.append(filename)
                    if filename not in current_playback_filenames:
                        copyfile(filepath, os.path.join(self.playback_dir, filename))
            new_songs_info = []
            for song_filename in filenames:
                song_file_path = os.path.join(self.playback_dir, song_filename)
                with audioread.audio_open(song_file_path) as audio_file:
                    #print('Unsupported sound file!')#TODO Сделать окно предупреждения
                    duration = audio_file.duration    
                length = int(duration * 1000)
                song_name, file_type = os.path.splitext(song_filename)
                song_widget = SongWidget(parent=self,
                                         id=self.get_id(),
                                         path=song_file_path,
                                         name=song_name,
                                         file_type=file_type,
                                         length=length,
                                         waveform=[]
                                         )
                self.add_song_widget(song_widget)
                new_songs_info.append(self.list.get_song_info(song_widget))
        self.list.update_items(font_size=self.options.spinBoxFontSize.value(),
                            buttons_size=self.options.spinBoxButtonsSize.value(),
                            buttons_set=self.options.get_song_buttons_set().values())
        if filenames:
            self.save(check_filenames=False)
            if list_was_empty:
                self.player.enable(True)
                #self.player.load(self.song(0))
                self.set_row(0)
            self.get_waveforms(new_songs_info)
    
    def get_waveforms(self, songs_info):
        for info in songs_info:
            with audioread.audio_open(info.get('path')) as audio_file:
                #print('Unsupported sound file!')#TODO Сделать окно предупреждения
                channels = audio_file.channels 
                samplerate = audio_file.samplerate
                duration = audio_file.duration
                print(channels, samplerate, duration)
                #print('total samples:', samplerate * duration)
                width = (BASE_WAVEFORM_DISPLAY_WIDTH - PLAYBACK_SLIDER_WIDTH_OFFSET - 
                                PLAYBACK_SLIDER_WAVEFORM_OFFSET)
                #print('WIDTH:', width)
                total_samples = int(channels * samplerate * duration)
                step = total_samples // width
                read_pos = 0
                samples = []
                first_buf = True
                for buf in audio_file:
                    buf_int = memoryview(buf).cast('h')
                    if first_buf:
                        buf_size = len(buf_int)
                        total_buffers = total_samples // buf_size
                        buffers_per_step = total_buffers // width
                        buf_count = buffers_per_step
                        first_buf = False
                    if not buf_count:
                        QCoreApplication.processEvents()
                        byte_L = buf_int[0]
                        byte_R = buf_int[1]
                        sample = max((abs(byte_L), abs(byte_R)))
                        samples.append(sample)
                        buf_count = buffers_per_step
                    else:
                        buf_count -= 1
                print(f'{info.get("name")} -- samples extracted!')
                waveform = []
                frame = deque(maxlen=WAVEFORM_AVERAGING_FRAME_WIDTH)
                max_sample = max(samples)
                print('Max sample:', max_sample)
                for sample in samples:
                    sample = int(self.scale_number(sample, 0, WAVEFORM_HEIGHT, 0, max_sample))
                    frame.append(sample)
                    if len(frame) >= WAVEFORM_AVERAGING_FRAME_WIDTH:
                        sample_averaged = int(sum(frame) / WAVEFORM_AVERAGING_FRAME_WIDTH)
                        waveform.append(sample_averaged)
                print('Max waveform:', max(waveform))
                self.list.set_waveform(info.get('id'), waveform)
    
    def add_song_widget(self, song_widget, row=False):
        item = QtWidgets.QListWidgetItem()
        if row is False:
            self.list.addItem(item)
        else:
            self.list.insertItem(row, item)
        self.list.setItemWidget(item, song_widget)
        if song_widget.muted:
            song_widget.buttonPlay.setDisabled(True)

    def duplicate_song_widget(self, parent_song):
        song_widget = SongWidget(parent=self,
                                id=self.get_id(),
                                path=parent_song.path,
                                name=parent_song.name,
                                file_type=parent_song.file_type,
                                volume=parent_song.volume,
                                length=parent_song.length,
                                start_pos=parent_song.start_pos,
                                end_pos=parent_song.end_pos,
                                repeat_mode=parent_song.repeat_mode,
                                fade_range=parent_song.fade_range,
                                muted=parent_song.muted,
                                waveform=parent_song.waveform
                                )
        parent_index = self.list.get_song_index(parent_song)
        self.add_song_widget(song_widget, row=parent_index + 1)
        if parent_index < self.playing:
            self.playing += 1
        if parent_index < self.selected:
            self.selected += 1
        self.list.update_items(font_size=self.options.spinBoxFontSize.value(),
                            buttons_size=self.options.spinBoxButtonsSize.value(),
                            buttons_set=self.options.get_song_buttons_set().values())

    def delete_song_widget(self, song):
        #delete_index = self.list.currentRow()
        delete_index = self.list.get_song_index(song)
        if delete_index == self.playing and self.player.state is not STOPED:
            self.show_message_box(DELETE_PLAYING_WARNING, cancel_text='')
        elif self.show_message_box('Точно удалить?') == OK:
                if delete_index < self.playing:
                    self.playing -= 1
                self.list.takeItem(delete_index)
                if self.is_empty():
                    self.player.enable(False)
                self.save(check_filenames=False)
                if self.is_empty():
                    self.player.eject()
    
    def save_list_name(self):
        delete_old_list = self.options.checkBoxRenameDeleteOldList.isChecked()
        new_name = self.lineListHeader.text()
        new_file_name = new_name + SONG_LIST_EXTENSION
        save_dir = os.path.dirname(self.save_file_path)
        if (not self.find_files((new_file_name,), save_dir) or
                    self.show_message_box(LIST_FILE_EXISTS_WARNING.format(new_name), 
                                          ok_text='Перезаписать', default_button=CANCEL)
                                          == OK):
            new_save_file_path = os.path.join(save_dir, new_name+SONG_LIST_EXTENSION).lower()
            old_save_file_path = os.path.normpath(self.save_file_path.lower())
            new_save_file_path = os.path.normpath(new_save_file_path.lower())
            print('OLD:', old_save_file_path)
            print('NEW:', new_save_file_path)
            if new_save_file_path != old_save_file_path:
                new_save_file_path = os.path.abspath(new_save_file_path)
                self.save_as(new_save_file_path)
                if (os.path.exists(old_save_file_path) and
                         not self.new_list_created and
                         self.options.checkBoxRenameDeleteOldList.isChecked()
                         ):
                    os.remove(old_save_file_path)
                    self.player.eject()
                    rmtree(self.get_playback_dir_path(old_save_file_path))
                self.buttonListHeader.setText(new_name)
                self.buttonListHeader.setToolTip(new_name)
        self.normal_mode()
        self.new_list_created = False
        if not self.is_empty():
            self.player.load(self.song(self.playing))
        else:
            self.player.enable(False)
    
    def new_list(self):
        self.save()
        self.clear(silent=True)
        new_list_name = self.get_new_list_path(just_name=True)
        self.new_list_created = True
        self.rename_mode(name=new_list_name)
    
    def get_new_list_path(self, just_name=False):
        save_name = DEFAULT_SONGLIST_NAME
        while True:
            save_file_path = os.path.join(self.options.save_dir(), save_name + SONG_LIST_EXTENSION)
            if os.path.exists(save_file_path):
                with open(save_file_path) as save_file:
                    if json.load(save_file):
                        save_name += '_копия'
                    else:
                        break
            else:
                break
        if just_name:
            return save_name
        return save_file_path
    
    def save(self, check_filenames=True, silent=False):
        print('SAVE: [silent:', silent, end='] ')
        list_name = os.path.basename(self.save_file_path).partition('.')[0]
        self.buttonListHeader.setText(list_name)
        self.buttonListHeader.setToolTip(list_name)
        songs_info = []
        for song_info in self.list.get_all_songs(info=True):
            print(song_info.get('name')[:3], end=', ')
            song_info.pop('path')
            songs_info.append(song_info)
        #print('Save file path:', self.save_file_path)
        with open(self.save_file_path, 'w') as save_file:
            json.dump(songs_info, save_file, indent=4)
            #json.dump(list(reversed(songs_info)), save_file, indent=4)
        if check_filenames:
            song_filenames = [song_info.get('name')+song_info.get('file_type') for song_info in songs_info]
            for filename in self.find_files(file_list=song_filenames, 
                                            search_dir=self.playback_dir,
                                            search_in_list=True,
                                            not_found=True):
                message_result = None
                if not silent:
                    warning = SOURCE_DELETE_WARNING.format(filename.partition('.')[0])
                    message_result = self.show_message_box(warning, 
                                                    ok_text='Удалить',
                                                    cancel_text='Оставить', 
                                                    checkbox_text='Применить ко всем')
                if silent or message_result == OK or message_result == OK_CHECKED:
                    os.remove(os.path.join(self.playback_dir, filename))
                    print('REMOVED:', filename)
                    if message_result == OK_CHECKED:
                        print('silent = True')
                        silent = True
                elif message_result == CANCEL_CHECKED:
                    break                
        print('saved')
    
    def save_as(self, save_file_path='', blank=False):
        if not save_file_path:
            save_file_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Файл сохранения',
                                     os.path.join('.', self.options.save_dir()), 'SongList File (*.sl)')[0]
            self.player.setFocus()
        if save_file_path and save_file_path != self.save_file_path:
            playback_dir_path = self.get_playback_dir_path(save_file_path)
            if os.path.exists(playback_dir_path):
                rmtree(playback_dir_path)#TODO Предупреждение, что такой список уже есть.
            os.mkdir(playback_dir_path)
            self.playback_dir = playback_dir_path
            if not blank:
                for song in self.list.get_all_songs():
                    new_song_path = os.path.join(playback_dir_path, song.name + song.file_type)
                    copyfile(song.path, new_song_path)
                self.list.set_playback_dir(playback_dir_path)
            self.save_file_path = save_file_path
        self.save()
                  
    def load(self, load_file_path=''):
        print('LOAD SONGLIST')
        if self.save_file_path:
            self.save()
        if not load_file_path:
            load_file_path = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                    'Загрузка списка песен', 
                                                    self.options.save_dir(), 
                                                    F'SongList File (*{SONG_LIST_EXTENSION})',
                                                    )[0]
            self.player.setFocus()
        if load_file_path and self.project_is_valid(load_file_path):
            print('file path:', load_file_path)
            self.save_file_path = load_file_path
            self.playback_dir = self.get_playback_dir_path(load_file_path)  
            with open(load_file_path, 'r') as load_file:
                songs_info = json.load(load_file)
            if not self.is_empty():
                self.player._stop()
                self.player.eject()
                self.clear(silent=True)            
            if songs_info:
                self.add_songs(songs_info=songs_info)
                row_changed = self.set_row(0, playing=True)
                if not row_changed:
                    self.player.load(self.song(self.playing))
                self.normal_mode()
            else:
                self.player.enable(False)
            self.save()
            
    def clear(self, silent=False):
        result = False
        if not self.is_empty():
            message_result = None
            if not silent:
                message_result = self.show_message_box(CLEAR_WARNING, 
                                                    ok_text='Очистить',
                                                    checkbox_text='Удалить также и файлы песен')
            if silent or message_result == OK or message_result == OK_CHECKED:
                self.list.clear()
                self.player.eject()
                self.player.enable(False)
                if message_result == OK_CHECKED:
                    self.save(silent=True)
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
            self.save_file_path = self.get_new_list_path()
            music_dir_path = self.get_playback_dir_path(self.save_file_path)
            if os.path.exists(music_dir_path):
                rmtree(music_dir_path)
            os.mkdir(music_dir_path)
            self.playback_dir = music_dir_path
            self.save(check_filenames=False)
        self.player.setFocus()
    
    def project_is_valid(self, load_file_path):
        print('PROJECT VALIDATION')
        valid = False
        with open(load_file_path, 'r') as load_file:
            songs_info = json.load(load_file)
        file_names_list = [song_info.get('name') + song_info.get('file_type') for song_info in songs_info]
        playback_dir = self.get_playback_dir_path(load_file_path)
        if not os.path.exists(playback_dir):
            print('playback dir not exist!')
            message_result = self.show_message_box(FOLDER_NOT_FOUND_WARNING, 
                                            ok_text='Указать папку',
                                            cancel_text='Отменить загрузку списка')
            if message_result == OK:
                new_playback_dir = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                        'Выбрать папку',
                                                        self.options.save_dir())
                if new_playback_dir:
                    os.mkdir(playback_dir)
                    for file_name in self.find_files(file_names_list, new_playback_dir, search_in_list=True):
                        copyfile(os.path.join(new_playback_dir, file_name), 
                                 os.path.join(playback_dir, file_name))
                    return self.project_is_valid(load_file_path)
        else:
            print('playback dir is valid...')
            files_not_found = self.find_files(file_names_list, playback_dir, not_found=True)    
            file_path = ''
            show_choice = True
            while files_not_found:
                file_name = files_not_found[0]
                warning = SONGFILE_NOT_FOUND_WARNING.format(file_name)
                print('files not found:', files_not_found)
                if show_choice:
                    choice_result = self.show_message_box(warning, 
                                                    ok_text='Найти файл',
                                                    cancel_text='Удалить песню из списка',
                                                    middle_text='Отменить загрузку списка', 
                                                    checkbox_text='Для всех файлов')
                if choice_result == OK or choice_result == OK_CHECKED:
                    relevant_file_name = self.get_relevant_file_name(file_name)
                    file_path = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                    F'Найти файл {file_name}',
                                                    self.options.save_dir(),
                                                    F'*{relevant_file_name}')[0]
                    
                    if file_path:
                        print('file_path recieved...')
                        try_playback_dir, try_file_name = os.path.split(file_path)
                        warning = WRONG_FILE_NAME_WARNING.format(file_name, try_file_name)
                        if try_file_name != file_name and self.show_message_box(warning, 
                                                    ok_text='Добавить файл',
                                                    cancel_text='Найти другой файл',
                                                    default_button=CANCEL,
                                                    ) == CANCEL:
                            print('wrong file! Try to find another')
                            file_path = ''
                            continue 
                        if choice_result == OK_CHECKED:
                            print('apply to all files:')
                            show_choice = False
                            for try_file_name in self.find_files(files_not_found, try_playback_dir):
                                print('found file:', try_file_name)
                                copyfile(os.path.join(try_playback_dir, try_file_name), 
                                         os.path.join(playback_dir, try_file_name))
                                files_not_found.remove(try_file_name)
                                print('file copied to', os.path.join(playback_dir, try_file_name))
                            if files_not_found:
                                print('some files are not found')
                                choice_result = OK
                                file_path = ''
                        else:
                            copyfile(file_path, os.path.join(playback_dir, file_name))
                            files_not_found.remove(file_name)
                    else:
                        show_choice = True
                elif choice_result == CANCEL or choice_result == CANCEL_CHECKED:
                    print('deleting song', file_name)
                    if choice_result == CANCEL_CHECKED:
                        songs_info = self.remove_info_by_filename(files_not_found, songs_info)
                        print('all songs removed.')
                        files_not_found.clear()
                        file_path = 'pass'
                    else:
                        #file_names_list.remove(file_name)
                        files_not_found.remove(file_name)
                        songs_info = self.remove_info_by_filename((file_name,), songs_info)
                        file_path = 'pass'
                elif choice_result == MIDDLE or choice_result == MIDDLE_CHECKED:
                    valid = False
                    return
            print('all files found. VALIDATED!')
            valid = True
        with open(load_file_path, 'w') as save_file:
            json.dump(songs_info, save_file)
        return valid    
    
    def get_relevant_file_name(self, file_name):
        name, sep, extension = file_name.rpartition('.')
        relevant_name = name
        index = max(name.rfind(' '), name.rfind('.'))
        if index >= 0:
            relevant_name = name[index+1:]
        return sep.join((relevant_name, extension))
            
    def find_files(self, file_list, search_dir, search_in_list=False, not_found=False):
        search_here = self.get_playback_dir_filenames(search_dir)
        look_for = file_list   #каждый файл списка ищем среди файлов папки
        if search_in_list:
            search_here = file_list     #каждый файл папки ищем среди файлов списка
            look_for = self.get_playback_dir_filenames(search_dir)
        search_here_casefolded = tuple(file_name.casefold() for file_name in search_here) 
        result = []
        for file_name in look_for:
            if file_name.casefold() in search_here_casefolded and not not_found:
                result.append(file_name)
            elif not file_name.casefold() in search_here_casefolded and not_found:
                result.append(file_name)
        return result
    
    def remove_info_by_filename(self, song_filenames, songs_info):
        new_songs_info = []
        for song_info in songs_info:
            song_filename = song_info.get('name')+song_info.get('file_type')
            print('searching...', song_info.get('name'))
            if not song_filename in song_filenames: 
                new_songs_info.append(song_info)
            else:
                print('song removed')
        return new_songs_info
                
    def set_row(self, target, playing=False):
        if type(target) != int:
            row = self.list.get_song_index(target)    
        else:
            row = target
        current_row = self.list.currentRow()
        print('SET ROW from',current_row , 'to', row)
        self.list.setCurrentRow(row) # смена строки вызывает change_row,
        row_changed = current_row != row # если строка поменялась
        if not row_changed:
            self.change_row(row)
        if playing:                  
            self.playing = row
        return row_changed
             
    def change_row(self, row):
        print()
        print('CHANGE ROW')
        self.selected = row
        print('SELECTED SONG INDEX:', self.selected)
        #print('Player_state:', self.player.state)
        if self.player.state is STOPED:
            self.playing = row
            song = self.song(self.playing)
            if song:
                self.player.eject()
                self.player.load(song)
                self.normal_mode()
            else:
                print('Song widget not detected!')
                self.player.enable(False)
        if self.renamed_song:
            self.renamed_song.normal_mode()
            
    def rename_song(self, list_item=None):
        self.renamed_song = self.list.itemWidget(list_item)
        self.renamed_song.rename()

    def mute_song(self, song):
        self.save(check_filenames=False)
        if song.muted:
            song.buttonPlay.setDisabled(True)
            if song == self.song(self.selected):
                self.player.enable(False, just_playback=True)
            if song == self.song(self.playing) and self.player.state == PLAYING:
                self.player._stop()
        else:
            song.buttonPlay.setEnabled(True)
            self.player.enable(just_playback=True)
        
    def rename_mode(self, name=None):
        self.player.enable_controls(False)
        self.buttonListHeader.hide()
        self.lineListHeader.show()
        self.lineListHeader.setText(name or self.buttonListHeader.text())
        self.lineListHeader.selectAll()
        self.lineListHeader.setFocus()

    def normal_mode(self):
        song = self.song(self.playing)
        self.player.enable(bool(song and not song.muted), just_playback=True)
        self.buttonListHeader.show()
        self.lineListHeader.hide()
        self.lineListHeader.clearFocus()
        self.player.setFocus()
        
    def show_message_box(self, message, 
                               checkbox_text='', 
                               ok_text='OK', 
                               cancel_text='Отмена',
                               middle_text='',
                               default_button=OK):
        message_box = QtWidgets.QMessageBox()
        message_box.setText(message)
        ok_button = message_box.addButton(ok_text,QtWidgets.QMessageBox.AcceptRole)
        middle_button = message_box.addButton(middle_text, QtWidgets.QMessageBox.RejectRole)
        cancel_button = message_box.addButton(cancel_text, QtWidgets.QMessageBox.RejectRole)
        middle_button.hide()
        cancel_button.hide()
        buttons = (ok_button, middle_button, cancel_button)
        message_box.setDefaultButton(buttons[default_button])
        checkbox = None
        if middle_text:
            middle_button.show()
        if cancel_text:
            cancel_button.show()
        if checkbox_text:
            checkbox = QtWidgets.QCheckBox(checkbox_text, message_box)
            message_box.setCheckBox(checkbox)
        result = message_box.exec()
        if checkbox and checkbox.isChecked():
            result += 3
        print('MESSAGE BOX RESULT:', result)
        return result
        
    def get_playback_dir_filenames(self, playback_dir=''):
        playback_dir = playback_dir or self.playback_dir
        return [f_name.strip() for f_name in os.listdir(playback_dir
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
        if raw_drop_index == -1: # песню утянули в самый низ списка
            raw_drop_index = self.count() - 1
            drop_indicator = 2
        if raw_drop_index >= from_index:
            drop_index = raw_drop_index + (drop_indicator - 2)
        else:
            drop_index = raw_drop_index + (drop_indicator - 1)
        if drop_index != from_index:
            playing = self.widget.playing
            #print('playing song index', playing)
            if playing == from_index:
                self.widget.playing = drop_index
            elif from_index < playing and drop_index >= playing:
                self.widget.playing -= 1
            elif from_index > playing and drop_index <= playing:
                self.widget.playing += 1
            print('drop indicator position:', self.dropIndicatorPosition())
            print('from index', from_index)
            print('drop index', drop_index)
            print('playing index =', self.widget.playing)
            super().dropEvent(event)
            self.widget.change_row(drop_index)
            self.widget.save()
            self.update_items()
        
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
                    'repeat_mode': song.repeat_mode,
                    'fade_range': song.fade_range,
                    'muted': song.muted,
                    'waveform': song.waveform#''.join([str(sample) for sample in waveform]),
        }
        return song_info
        
    def set_playback_dir(self, playback_dir):
        for song in self.get_all_songs():
            song.path = os.path.join(playback_dir, song.name+song.file_type)
            
    def update_items(self, font_size=None,
                           buttons_size=None,
                           buttons_set=None):
        if font_size and buttons_size and buttons_set:                   
            item_height = max(font_size, buttons_size) + 10
        items_set = range(self.count())
        for i in items_set:
            item = self.item(i)
            song = self.itemWidget(item)
            if font_size and buttons_size and buttons_set: 
                item.setSizeHint(QtCore.QSize(1, item_height))
                song.update_font(size=font_size)
                song.update_buttons_size(buttons_size)
                song.update_buttons_set(buttons_set)
            song.update_number(i + 1)
 
    def set_waveform(self, id_, waveform):
        for index, song in enumerate(self.get_all_songs()):
            if song.id == id_:
                song.set_waveform(waveform)
                if index == self.widget.playing:
                    self.widget.player.waveform = waveform
                    self.widget.player.resize_waveform()
                    self.widget.player.update()

                   
class ClickerPlayerApp(QtWidgets.QMainWindow):
    START_VOLUME = 50
    MAX_VOL = 100
    MIN_VOL = 0
    VOLUME_STEP = 5
    #end_of_playback = QtCore.pyqtSignal()
    
    def __init__(self,):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        #self.setStyleSheet("#centralwidget{background-color:green}")
        
        self.PLAY_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/play.png'))
        self.PAUSED_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/pause.png'))
        self.START_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/start.png'))
        self.END_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/end.png'))
        self.FADEIN_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/fadein.png'))
        self.FADEOUT_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/fadeout.png'))
        self.PLAY_ALL_ICON = QtGui.QIcon(QtGui.QPixmap(':/player/icons/dont_repeat.png'))
        self.REPEAT_ALL_ICON = QtGui.QIcon(QtGui.QPixmap(':/player/icons/repeat.png'))
        self.PLAY_ONE_ICON = QtGui.QIcon(QtGui.QPixmap(':player/icons/dont_repeat_one.png'))
        self.REPEAT_MODES = {PLAY_ONE: {'checked': True, 'icon':  self.PLAY_ONE_ICON},
                        PLAY_ALL: {'checked': False, 'icon':  self.PLAY_ALL_ICON},
                        REPEAT_ALL: {'checked': True, 'icon':  self.REPEAT_ALL_ICON},
                       }
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
        
        self.deck_L = QMediaPlayer()
        self.deck_L.setNotifyInterval(250)
        self.deck_L.positionChanged.connect(self.update_playback_slider)
        self.deck_L.stateChanged.connect(self.deck_state_changed)
        #self.end_of_playback.connect(self.play_next)
        #self.deck_R = QMediaPlayer()
        
        self.play_next_switch = False
        self.allow_playback_update = True
        self.allow_volume_update = True
        self.playback_update_thread = None
        self.volume_update_thread = None
        self.high_acuracy = False
        self.song_volume = 100
        self.fade_raitos = (0, 0)
        self.master_volume = self.START_VOLUME
        self.state = STOPED
        self.enabled = True
        self.repeat_mode = self.prev_repeat_mode = PLAY_ALL
        
        self.beep = QMediaPlayer()
        content = QMediaContent(QUrl.fromLocalFile(DEFAULT_SIGNAL_PATH))
        self.beep.setMedia(content)
        
        self.waveform = []
        
        self.options = OptionsDialog(OPTIONS_FILE_PATH, self)
        self.presentation_mode = False
        
        self.buttonOptions.clicked.connect(self.options.show)
        self.buttonPrevious.clicked.connect(self.play_previous)
        self.buttonStop.clicked.connect(self._stop)
        self.buttonPlay.clicked.connect(self.play_pause)
        self.buttonPause.clicked.connect(self.play_pause)
        self.buttonNext.clicked.connect(self.play_next)
        
        self.buttonRepeat.clicked.connect(self.set_repeat)
        self.set_repeat_to(PLAY_ALL)
        
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
        
        self.show_automations(False)
        
        self.list = SongListWidget(self, self.options)
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
                                                    
                                                    
        save_file_path = self.options.last_playlist_path  # делается здесь, потому что self.list 
        if not os.path.exists(save_file_path):            # уже должен существовать для корректной работы
            save_file_path = self.list.get_new_list_path()# его методов.
            self.list.save_as(save_file_path)
        else:
            self.list.load(save_file_path)   
        if self.list.is_empty():
            self.enable(False)
        self.setFocus()
    
    def deck_state_changed(self, state):
        print('DECK state changed to', state, 'deck position:', self.deck_L.position())
        song = self.list.song(self.list.playing)
        #print('SONG end_pos:', song.end_pos)
        if state == STOPED:
            if abs(self.deck_L.position() - song.end_pos) < 100:
                self.play_next_switch = True
                self.play_next()
      
    def _play(self):
        self.play_beep()
        song = self.list.song(self.list.playing)
        self.state = PLAYING
        self.buttonPlay.setChecked(True)
        self.buttonPause.setChecked(False)
        song.buttonPlay.setIcon(self.PLAY_ICON)
        song.buttonPlay.setChecked(True)
        self.allow_automations_update()
        self.start_volume_update()
        self.deck_L.play()
        print('PLAYING...', self.list.playing,  song.name)
           
    def _pause(self):
        song = self.list.song(self.list.playing)
        self.play_beep()
        self.deck_L.pause()
        self.state = PAUSED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(True)
        song.buttonPlay.setIcon(self.PAUSED_ICON)
        song.buttonPlay.setChecked(True)
        print('PAUSED...')
                
    def _stop(self, event=None):
        self.play_beep()
        print('_STOP -- ')
        self.deck_L.stop()
        self.state = STOPED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(False)
        song = self.list.song(self.list.playing)
        if song:
            song.buttonPlay.setIcon(self.PLAY_ICON)
            song.buttonPlay.setChecked(False)
            self.change_pos(song.start_pos)
        else:
            self.change_pos(0)
        if (self.sender() == self.buttonStop and
                 song != self.list.song(self.list.selected)):
            self.eject()
            self.list.set_row(self.list.selected, playing=True)
            self.load(self.list.song(self.list.playing))  
        print('STOPED...')
        
    def play_pause(self, event=None, song=None):   
        self.play_beep()
        print('PLAY|PAUSE')
        if song and song != self.list.song(self.list.playing):
            self._stop()
            self.eject()
            self.list.set_row(song, playing=True)
            #self.load(sender)
        elif not self.enabled:
            print('Controls disabled!')
            return
        if self.state == STOPED:
            if self.list.song(self.list.playing) != self.list.song(self.list.selected):
                self.eject()
                self.list.set_row(self.list.selected, playing=True)
                #self.load(self.list.song(self.list.selected))
            self._play()
            if self.sender() and self.sender() == self.buttonPause:
                self._pause()
        else:
            if self.state == PAUSED or not self.deck_L.state() == PLAYING:
                self._play()
            else:
                self._pause()
            
    def play_next(self):
        print('PLAY NEXT')
        self.play_beep()
        self._stop()
        next_song = self.get_next_song()
        if (next_song and 
                (self.sender() == self.deck_L or 
                self.options.checkBoxAutoplayFforw.isChecked() or
                next_song.repeat_mode == REPEAT_ONE)):
            self._play()
        self.play_next_switch = False
        print('play next switched to False')
                
    def get_next_song(self):
        current_song = self.list.song(self.list.playing)
        #print('GET NEXT SONG')
        repeat_mode = self.repeat_mode
        #print('repeat mode:', repeat_mode)
        next_song = None
        if current_song.repeat_mode == REPEAT_ONE:
            if self.play_next_switch:
                print('repeat one')
                next_song = current_song
                self.load(next_song)
            else:
                print('temporary PLAY ALL')
                repeat_mode = PLAY_ALL #зачем?!
        elif repeat_mode == PLAY_ALL or repeat_mode == REPEAT_ALL:
            print('play/repeat all')
            song = self.list.get_song('next')
            while song and song.muted:
                song = self.list.get_song('next')
            if song:
                next_song = song
            elif repeat_mode == REPEAT_ALL:
                self.list.playing = 0
                self.list.set_current_row(0)
                song = self.list.song(0)
                while song and song.muted:
                    song = self.list.get_song('next')
                next_song = song
        return next_song
    
    def play_previous(self, event=None):
        self.play_beep()
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
        
    def update_playback_slider(self, playback_pos):
        song = self.list.song(self.list.playing)
        if self.state == PLAYING and self.deck_L.position() >= song.end_pos and not self.play_next_switch:
            self.play_next_switch = True
            self.play_next()
            #self.end_of_playback.emit()
            #print('END OF PLAYBACK emited')
            return
        if self.allow_playback_update:
            self.sliderPlaybackPos.setValue(playback_pos)
        if playback_pos % 1000 < 250:
            current_min_sec, current_millisec = self.min_sec_from_ms(playback_pos, show_ms=True)
            self.labelCurrentPos.setText(current_min_sec)
            if self.high_acuracy:
                self.labelCurrentPosMs.setText(current_millisec)
                if self.allow_playback_update:
                    self.high_acuracy = False
            else:
                self.labelCurrentPosMs.hide()
    
    def _update_volume_automation(self, song, playback_pos):
        #print('VOLUME AUTOMATION --')
        fade_volume = 0
        while (self.allow_volume_update and
                self.state == PLAYING):
            playback_pos = self.deck_L.position()
            if song.faded and playback_pos % 250 < 20:
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
    
    def start_volume_update(self):
        if self.volume_update_thread:
            if self.volume_update_thread.is_alive():
                self.allow_automations_update(playback=None, volume=False)
        song =  self.list.song(self.list.playing)
        playback_pos = self.deck_L.position() #дублировано для проверки повтора
        #to_end_delta = song.end_pos - playback_pos #дублировано для проверки перехода
        print('START VOLUME AUTOMATION')
        self.allow_automations_update(playback=None, volume=True)
        self.volume_update_thread = Thread(target=self._update_volume_automation,
               args=(song, playback_pos))
        self.volume_update_thread.start()
                       
    def change_pos(self, pos=None):
        #print('CHANGE_POS --')
        #print('pos:', pos)
        if pos == None: # отпущен слайдер позиции
            slider_pos = self.sliderPlaybackPos.value()
        else:   # нажата кнопка перемотки
            slider_pos = pos
        start_pos, end_pos = self.sliderPlaybackRange.value()
        if slider_pos < start_pos:
            slider_pos = start_pos
        elif slider_pos > end_pos:
            slider_pos = end_pos
        self.deck_L.setPosition(slider_pos)
        self.sliderPlaybackPos.setValue(slider_pos)
        current_min_sec, current_millisec = self.min_sec_from_ms(slider_pos, show_ms=True)
        self.labelCurrentPos.setText(current_min_sec)
        if self.high_acuracy:
            self.labelCurrentPosMs.show()
            self.labelCurrentPosMs.setText(current_millisec)
        print('CHANGE_POS: changed to', slider_pos)
        self.allow_automations_update(playback=True, volume=None)
    
    def change_range(self, pbrange=None):
        song = self.list.song(self.list.playing)
        prev_fadein, prev_fadeout = song.fade_range
        prev_start, prev_end = song.start_pos, song.end_pos
        prev_fadein_delta = prev_fadein - prev_start
        prev_fadeout_delta = prev_fadeout - prev_end
        if not pbrange:  #slider released
            start_pos, end_pos = self.sliderPlaybackRange.value()
        else:       #button set range
            start_pos, end_pos = pbrange
            self.sliderPlaybackRange.setValue(pbrange)
        if (song.start_pos, song.end_pos) != (start_pos, end_pos):
            song.set_playback_range((start_pos, end_pos))
            self.list.save()
        self.labelEndPos.setText(self.min_sec_from_ms(end_pos))
        if self.sliderPlaybackPos.value() < start_pos:
            self.change_pos(start_pos)
        elif self.sliderPlaybackPos.value() > end_pos:
            self.change_pos(end_pos)
        fade_in = song.start_pos + max(prev_fadein_delta, 0)
        fade_out = song.end_pos + min(prev_fadeout_delta, 0)
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
        new_slider_pos = self.sliderPlaybackPos.value() - self.options.spinBoxChangePosStep.value()
        if new_slider_pos >= 0:
            self.high_acuracy = True
            self.deny_playback_automation()
            self.change_pos(new_slider_pos)
        
    def step_fforward(self):
        new_slider_pos = self.sliderPlaybackPos.value() + self.options.spinBoxChangePosStep.value()
        if new_slider_pos <=  self.list.song(self.list.playing).length:
            self.high_acuracy = True
            self.deny_playback_automation()
            self.change_pos(new_slider_pos)
    
    def load(self, song):
        print('LOAD')
        if song:
            self.waveform = song.waveform
            self.resizeEvent(QtGui.QResizeEvent)
            if not song.muted:
                content = QMediaContent(QUrl.fromLocalFile(song.path))
                self.deck_L.setMedia(content)
                self.deck_L.setPosition(song.start_pos)
                #print('start pos:', song.start_pos)
                song.buttonDelete.setEnabled(True)
                self.enable(just_playback=True)
                self.sliderPlaybackPos.setMaximum(song.length)
                self.sliderPlaybackRange.setMaximum(song.length)
                self.sliderFadeRange.setMaximum(song.length)
                #pdb.set_trace()
                self.change_range((song.start_pos, song.end_pos))
                self.sliderSongVol.setValue(song.volume)
                if song.faded or song.range_limited or self.options.checkBoxShowAutomations.isChecked():
                    self.show_automations()
                    if self.fade_raitos[0]:
                        self.sliderSongVol.setValue(0)
                print('song', song.name[:20], 'was loaded')
                self.update()
            else:
                print('song not loaded because it is muted')
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
                    
    def min_sec_from_ms(self, milliseconds, show_ms=False):
        sec_float = milliseconds / 1000
        sec_int = int(sec_float)
        millisec = int((sec_float - sec_int) * 1000)
        minutes = sec_int // 60
        sec = sec_int % 60
        if show_ms:
            result = (f'{minutes :02.0f}:{sec :02.0f}', f'{millisec :03.0f}')
        else:
            result = f'{minutes :02.0f}:{sec :02.0f}'
        return result
    
    def set_repeat(self):
        self.repeat_mode = (self.repeat_mode + 1) % 3
        if self.repeat_mode == PLAY_ONE:
            for song in self.list.list.get_all_songs():
                song.set_repeat_to(PLAY_ONE)
        elif self.prev_repeat_mode == PLAY_ONE:
            for song in self.list.list.get_all_songs():
                if song.repeat_mode == PLAY_ONE:
                    song.set_repeat_to(AS_LIST)
        self.set_repeat_to(self.repeat_mode)
        self.prev_repeat_mode = self.repeat_mode
        self.list.save()
    
    def set_repeat_to(self, mode):
        print('SET REPEAT TO', mode)
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
        self.song_volume = vol
        if move_slider: #слайдер вызывает этот же метод при перемещении, если его позиция изменилась
            self.sliderSongVol.setValue(self.song_volume)
        self.apply_volume()
        
    def song_vol_write(self,):
        print('song vol writed:', self.song_volume)
        self.list.song(self.list.playing).volume = self.song_volume
        self.change_fade_range()
        if self.state == PLAYING:
            self.start_volume_update()
            
    def apply_volume(self):
        mixer_volume = int((self.song_volume * self.master_volume) / 100)
        self.deck_L.setVolume(mixer_volume)
    
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
        #print('CHANGE FADE RANGE: fade_range:', fade_range)
        song = self.list.song(self.list.playing)
        if not fade_range:     #slider released
            fadein_pos, fadeout_pos = self.sliderFadeRange.value()
        else:               #set_fade_range
            fadein_pos, fadeout_pos = fade_range
        if song.fade_range != (fadein_pos, fadeout_pos):
            song.set_fading((fadein_pos, fadeout_pos))
            self.list.save()
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
        #print('GET FADE RAITOS --')
        #print('fade in:', fade_in, 'fade out', fade_out, 'volume:', song.volume)
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
        if self.list.show_message_box(RESET_SONG_SETTINGS_WARNING) == OK:
            self.master_vol_change(DEFAULT_MASTER_VOLUME)
            self.song_vol_change(DEFAULT_SONG_VOLUME, move_slider=True)
            self.change_range((0,  self.list.song(self.list.playing).length))
            self.change_fade_range((0,  self.list.song(self.list.playing).length))
            self.list.song(self.list.playing).repeat_mode = AS_LIST
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
    
    def play_beep(self, enabled=None, volume=None):
        if enabled == None:
            enabled = self.options.checkBoxEnableSignals.isChecked()
        if volume == None:
            volume = self.options.beeps_volume
        if enabled:
            self.beep.setVolume(int(volume))
            self.beep.play()
    
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
    
    def resize_waveform(self):
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
               
    def closeEvent(self, event):
        self.options.save()
        self.deny_playback_automation()
        self.deny_volume_automation()
        self.deck_L.stop()
        self.list.save()
        event.accept()
    
    def resizeEvent(self, event=None):
        if self.options.checkBoxShowWaveform.isChecked():
            self.resize_waveform()
        
    def paintEvent(self, event) -> None:  #a0: QtGui.QPaintEvent
        if self.options.checkBoxShowWaveform.isChecked():
            painter = QtGui.QPainter(self)
            painter.setBrush(QtCore.Qt.lightGray)
            pos = self.sliderPlaybackPos.pos()
            rect = self.sliderPlaybackPos.rect()
            shift_x = 8 # половина ширины ручки слайдера
            shift_y = -1
            #print(pos.x(), pos.y(), rect.width(), rect.height())
            start_x = pos.x() + shift_x
            start_y = pos.y() + int(rect.height() / 2) + shift_y
            polygon = QtGui.QPolygon()
            polygon.append(QtCore.QPoint(start_x, start_y))
            for i, sample in enumerate(self.waveform):
                polygon.append(QtCore.QPoint(start_x + i, start_y - sample))
            polygon.append(QtCore.QPoint(start_x + len(self.waveform), start_y))
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