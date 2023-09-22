# -*- coding: utf-8 -*-

import json
import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from pygame import mixer
from superqt import QRangeSlider
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from shutil import copyfile, rmtree
from time import sleep
from threading import Thread
from threading import active_count as active_threads

VALID_SYMBOL_CODES = (tuple(chr(s) for s in range(1040, 1104)) + 
                        tuple(chr(s) for s in range(128)) + ('ё', 'Ё'))

SONG_ITEM_UI_PATH = 'GUI/songitem.ui'
SONG_LIST_UI_PATH = 'GUI/songList.ui'
MAIN_WINDOW_UI_PATH = 'GUI/main_window.ui'

mixer.init()
DEFAULT_PLAYBACK_DIR = 'song_lists/Новый список воспроизведения_music/'
DEFAULT_SAVE_DIR = 'song_lists/'
DEFAULT_SONGLIST_NAME = 'Новый список воспроизведения.sl'
SONG_LIST_EXTENSION = '.sl'

OPTIONS_FILE_PATH = 'assets/options.json'
DEFAULT_OPTIONS = {'last_playlist_path': os.path.join(DEFAULT_SAVE_DIR, DEFAULT_SONGLIST_NAME), 
                }

CLEAR_WARNING = 'Все несохранённые изменения будут утеряны! Очистить список?'
LOAD_WARNING = 'Загружаемый список заменит существующий.\nВсе несохранённые изменения будут утеряны. Продолжить?'
DELETE_PLAYING_WARNING = 'Нельзя удалить то, что сейчас играет!'
SOURCE_DELETE_WARNING = '''Песни {} больше нет в списке, но файл с ней ещё остался.
Если удалить файл, вы, возможно, не сможете восстановить его.
Если файл оставить, вы потом сможете снова добавить его в список\n
Cancel - оставить файл. Ок - удалить '''

CHANGE_POS_STEP = 250

STOPED = 0
PLAYING = 1
PAUSED = 2

OK = 1024

PLAY_LABEL = 'P'
PAUSED_LABEL = 'Paused'

LIST_ITEM_HEIGHT = 28
       

class SongWidget(QtWidgets.QWidget):
    def __init__(self, parent,
                       id,
                       path,
                       name,
                       length,
                       file_type='.mp3',
                       volume=50,
                       start_pos=0,
                       end_pos=0,
                       repeat=False,
                       fade_in=False,
                       fade_out=False,
                       muted=False,
                       ):
        super().__init__()
        self.id = id
        self.path = path
        self.name = name
        self.file_type = file_type
        self.volume = volume
        self.length = length
        self.start_pos = start_pos
        self.end_pos = end_pos
        if not end_pos:
            self.end_pos = length
        self.repeat = repeat
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.muted = muted
        self.song_list = parent
        
        uic.loadUi(SONG_ITEM_UI_PATH, self)
        self.labelSongName.setText(name)
        self.labelSongName.setToolTip(name)
        
        self.lineNewSongName.returnPressed.connect(self.save_name)
        self.lineNewSongName.hide()
        
    def rename(self):
        self.labelSongName.hide()
        self.lineNewSongName.show()
        self.lineNewSongName.setText(self.name)
        self.lineNewSongName.selectAll()
        self.lineNewSongName.setFocus()
        
    def save_name(self):
        self.name = self.lineNewSongName.text()
        self.labelSongName.setText(self.name)
        self.song_list.set_saved(False)
        self.normal_mode()
        
    def normal_mode(self):
        self.lineNewSongName.clearFocus()
        self.lineNewSongName.hide()
        self.labelSongName.show()


class SongListWidget(QtWidgets.QWidget):
    def __init__(self, player, initial_save_file_path):
        super().__init__()
        
        #GUI settings
        uic.loadUi(SONG_LIST_UI_PATH, self)
        self.list = SongList(self)
        self.layoutSongList.addWidget(self.list)
        
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
        self.previous_row = 0
        self.renamed_song = None
        self.id_source = 0
        self.saved = True
        self.playback_dir = DEFAULT_PLAYBACK_DIR
        if not os.path.exists(DEFAULT_SAVE_DIR):
            os.mkdir(DEFAULT_SAVE_DIR)
        self.save_file_path = ''
        if not os.path.exists(initial_save_file_path):
            self.save_as(DEFAULT_SONGLIST_NAME)
        else:
            self.load(initial_save_file_path)
        #self.playing_num = 0
        self.selected_song_index = 0
        self.playing_song_index = self.selected_song_index
        self.playing_song = self.list.get_song_by_index(self.selected_song_index)
        self.list.setCurrentRow(0)
        
    def add_songs(self, filenames=[], songs_info=[]):
        if songs_info:
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
                                        fade_in=info.get('fade_in'),
                                        fade_out=info.get('fade_out'),
                                        muted=info.get('muted'),
                                        )
                self.add_song_widget(song_widget)
        else:
            if not filenames:
                filepaths = QtWidgets.QFileDialog.getOpenFileNames(self, 
                                                        'Добавить дорржки', 
                                                        '.', 
                                                        'Music Files (*.mp3 *.wav)',
                                                        )[0]
                filenames = []
                current_playback_filenames = self.get_playback_dir_filenames()
                #print('Playback filenames:', current_playback_filenames)
                for filepath in filepaths:
                    filedir, filename = os.path.split(filepath) #СЮДА ПРОВЕРКУ НА КОРРЕКТНЫЕ СИМВОЛЫ В ИМЕНИ ФАЙЛА
                    improved_filename = self.improve_filename(filename)
                    if improved_filename:
                        filename = improved_filename
                        print('IMPROVED ! ! !')
                        pass # Окно предупреждения об удалении недопустимых символов
                    filenames.append(filename)
                    if filename not in current_playback_filenames:
                        copyfile(filepath, os.path.join(self.playback_dir, filename))
        
            for song_filename in filenames:
                song_file_path = os.path.join(self.playback_dir, song_filename)
                song_name, sep, file_type = song_filename.rpartition('.')
                print('FILE TYPE:', file_type)
                if file_type == 'mp3':
                    song_info = MP3(song_file_path).info
                elif file_type == 'WAV' or file_type == 'wav':
                    song_info = WAVE(song_file_path).info
                else:
                    print('Unsupported sound file!')#TODO Сделать окно предупреждения
                length = song_info.length
                length = int(length * 1000) #convert to int milliseconds
                song_widget = SongWidget(parent=self.list,
                                         id=self.get_id(),
                                         path=song_file_path,
                                         name=song_name,
                                         file_type=file_type,
                                         length=length,
                                         )
                self.add_song_widget(song_widget)
        if filenames:
            self.set_saved(False)
            self.player.playback_enable(True)
        #self.player.current_song = None
        # if hasattr(self.player, 'listSongs'):
        # self.player.load(self.list.get_song_by_index(0))
    
    def add_song_widget(self, song_widget):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(1, LIST_ITEM_HEIGHT)) #width based on parent, height = 28
        self.list.addItem(item)
        self.list.setItemWidget(item, song_widget)
        self.saved = False
    
        #song_widget.buttonPlay.setDisabled(True)
        song_widget.buttonPlay.clicked.connect(self.player.play_pause)
        song_widget.buttonRepeat.clicked.connect(self.player.set_repeat)
        song_widget.buttonDelete.setDisabled(True)
        song_widget.buttonDelete.clicked.connect(self.delete_song_widget)

    def delete_song_widget(self):
        delete_index = self.list.currentRow()
        if delete_index == self.playing_song_index and self.player.state is not STOPED:
            self.show_message_box(DELETE_PLAYING_WARNING, cancel=False)
        elif self.show_message_box('Точно удалить?') == OK:
                if delete_index < self.playing_song_index:
                    self.playing_song_index -= 1
                self.list.takeItem(delete_index)
                if self.list.count() < 1:
                    self.player.playback_enable(False)
                #     self.player.buttonSaveList.setDisabled(True)
                self.set_saved(False)
    
    def save_list_name(self):
        new_name = self.lineListHeader.text()
        new_save_file_path = os.path.join(os.path.dirname(self.save_file_path),
                                            new_name+SONG_LIST_EXTENSION)
        new_save_file_path = os.path.abspath(new_save_file_path) 
        old_save_file_path = self.save_file_path                                   
        #print('OLD PATH:', self.save_file_path)
        #print('NEW PATH:', new_save_file_path)
        self.save_as(new_save_file_path)
        os.remove(old_save_file_path)
        rmtree(self.get_playback_dir_path(old_save_file_path))
        self.normal_mode()
        self.buttonListHeader.setText(new_name)
        self.buttonListHeader.setToolTip(new_name)
    
    def save(self):
        if not self.saved:
            songs_info = []
            for song in self.list.get_all_songs():
                songs_info.append(self.list.get_song_info(song))
            #print('Save file path:', self.save_file_path)
            with open(self.save_file_path, 'w') as save_file:
                json.dump(list(reversed(songs_info)), save_file, indent=4)
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
        if save_file_path == self.save_file_path:
            print('called SAVE')
            self.save()
        else:
            music_dir_path = self.get_playback_dir_path(save_file_path)
            if save_file_path:
                songs_info = []
                if os.path.exists(music_dir_path):
                    rmtree(music_dir_path)
                os.mkdir(music_dir_path)
                self.playback_dir = music_dir_path
                for song in self.list.get_all_songs():
                    new_song_path = os.path.join(music_dir_path, song.name+'.'+song.file_type)
                    copyfile(song.path, new_song_path)
                    song.path = new_song_path
                    songs_info.append(self.list.get_song_info(song))
                with open(save_file_path, 'w') as save_file:
                    json.dump(list(reversed(songs_info)), save_file, indent=4)
                self.set_saved()
        self.save_file_path = save_file_path
        
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
        if not self.saved:
            if self.show_message_box(LOAD_WARNING) != OK:
                return
        if not load_file_path:
            load_file_path = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                    'Загрузка списка песен', 
                                                    '.', 
                                                    'SongList File (*.sl)',
                                                    )[0]
        if load_file_path:
            with open(load_file_path, 'r') as load_file:
                songs_info = json.load(load_file)
            # if self.list.count() > 0:# Не помню, для чего
            #pass
            self.clear()
            self.player.eject()
            if songs_info:
                self.add_songs(songs_info=songs_info)
                if hasattr(self.player, 'listSongs'):
                    self.playing_song_index = 0
                    self.playing_song = self.list.get_song_by_index(0)
                    self.selected_song_index = 0
                    self.list.setCurrentRow(0)
                    self.player.load(self.playing_song)
            self.save_file_path = load_file_path
            self.playback_dir = self.get_playback_dir_path(load_file_path)
            self.set_saved()
            self.player.playback_enable()

    def clear(self):
        if not self.saved:
            if self.show_message_box(CLEAR_WARNING) != OK:
                return
        self.player.playback_enable(False)
        self.list.clear()
        self.set_saved(True)

    def delete(self):
        pass
        
    def change_row(self, target):
        print('CHANGE ROW')
        if type(target) == int:
            row = target
            song = self.list.get_song_by_index(row)
        else:
            row = self.list.get_song_index(target)
            song = target
        prev_song = self.list.get_song_by_index(self.selected_song_index)
        if prev_song:
            prev_song.buttonDelete.setDisabled(True)
        else:
            print('prev_song widget not detected!')
        self.selected_song_index = row
        print('SELECTED SONG INDEX:', self.selected_song_index)
        if self.list.currentRow() != row:
            print('CURRENT ROW != selected index!!!')
            self.list.setCurrentRow(row)
        if song:
            song.buttonDelete.setEnabled(True)
            if song == self.playing_song:
                self.player.buttonRepeat.setChecked(song.repeat)
            if self.player.state is STOPED:
                self.player.eject()
                if hasattr(self.player, 'listSongs'):
                    self.player.load(song)
        else:
            print('Song widget not detected!') 
        if self.renamed_song:
            self.renamed_song.normal_mode()
        self.normal_mode()
        
    def rename_song(self, list_item=None):
        self.renamed_song = self.list.itemWidget(list_item)
        self.renamed_song.rename()

    def rename_mode(self):
        self.buttonListHeader.hide()
        self.lineListHeader.show()
        self.lineListHeader.setText(self.buttonListHeader.text())
        self.lineListHeader.selectAll()
        self.lineListHeader.setFocus()

    def normal_mode(self):
        self.buttonListHeader.show()
        self.lineListHeader.hide()
        self.lineListHeader.clearFocus()
        
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
        
    def get_selected_song(self):
        return self.list.get_song_by_index(self.selected_song_index)
        
    def get_song(self, direction=''):
        song = None
        if self.player.state == PLAYING or self.player.state == PAUSED:
            song_index = self.playing_song_index
        else:
            song_index = self.selected_song_index
            
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
            self.change_row(new_song_index)
            self.playing_song_index = new_song_index
            self.playing_song = self.list.get_song_by_index(new_song_index)
            song = self.playing_song
        else:
            print(message)
        return song
    
    def set_playing_song(self, song):
        self.playing_song_index = self.list.get_song_index(song)
        self.playing_song = song
    
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
            playing_song_index = self.widget.playing_song_index
            print('playing song index', playing_song_index)
            if playing_song_index == from_index:
                self.widget.playing_song_index = drop_index
            elif from_index < playing_song_index and drop_index >= playing_song_index:
                self.widget.playing_song_index -= 1
            elif from_index > playing_song_index and drop_index <= playing_song_index:
                self.widget.playing_song_index += 1
            self.widget.set_saved(False)
            print('drop indicator position:', self.dropIndicatorPosition())
            print('from index', from_index)
            print('drop index', drop_index)
            print('playing_song_index =', self.widget.playing_song_index)
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
        song_info = {'id': song.id,
                    'path': song.path,
                    'name': song.name,
                    'file_type': song.file_type,
                    'volume': song.volume,
                    'length': song.length,
                    'start_pos': song.start_pos,
                    'end_pos': song.end_pos,
                    'repeat': song.repeat,
                    'fade_in': song.fade_in,
                    'fade_out': song.fade_out,
                    'muted': song.muted,
        }
        return song_info
        
                    
class ClickerPlayerApp(QtWidgets.QMainWindow):
    START_VOLUME = 10
    MAX_VOL = 100
    MIN_VOL = 0
    VOLUME_STEP = 5
    def __init__(self,):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        
        self.controls = {QtCore.Qt.Key_Escape: self.play_next,
                         QtCore.Qt.Key_Shift: self.play_next,
                         QtCore.Qt.Key_Tab: self.play_pause,
                         QtCore.Qt.Key_Space: self.play_pause,
                         QtCore.Qt.Key_Up: self.vol_up, 
                         QtCore.Qt.Key_Down: self.vol_down,
                         QtCore.Qt.Key_B: self.play_previous,
                         QtCore.Qt.Key_Left: self.step_rewind, 
                         QtCore.Qt.Key_Right: self.step_fforward,
                         QtCore.Qt.Key_Z: self.qlist_info,
                         }
                         
        self.save_dir = DEFAULT_SAVE_DIR
        if os.path.exists(OPTIONS_FILE_PATH):
            with open(OPTIONS_FILE_PATH, 'r', encoding='utf-8') as options_file:
                self.options = json.load(options_file)
                if not self.options:
                    self.options = DEFAULT_OPTIONS
        else:
            self.options = DEFAULT_OPTIONS
            
        self.start_pos = 0
        self.allow_autopos = True
        self.high_acuracy = False
        self.volume = 0
        self.state = STOPED
        
        #self.current_track_num = 10000
        self.current_song = None
        
        self.listSongs = SongListWidget(self, self.options.get('last_playlist_path'))
        self.layoutSongList.addWidget(self.listSongs)
        
        self.buttonPrevious.clicked.connect(self.play_previous)
        self.buttonStop.clicked.connect(self._stop)
        self.buttonPlay.clicked.connect(self.play_pause)
        self.buttonPause.clicked.connect(self.play_pause)
        self.buttonNext.clicked.connect(self.play_next)
        
        self.buttonRepeat.clicked.connect(self.set_repeat)
        
        self.sliderVol.valueChanged.connect(self.vol_change)
        
        self.sliderPlaybackPos.sliderPressed.connect(self.deny_autopos)
        self.sliderPlaybackPos.sliderReleased.connect(self.change_pos)
        self.labelCurrentPosMs.hide()
        
        self.sliderPlaybackRange = QRangeSlider()
        self.sliderPlaybackRange.setOrientation(QtCore.Qt.Horizontal)
        self.sliderPlaybackRange.sliderReleased.connect(self.change_range)
        self.buttonSetStart = QtWidgets.QPushButton()
        self.buttonSetStart.setText('sSt')
        self.buttonSetStart.setFixedSize(54, 32)
        self.buttonSetEnd = QtWidgets.QPushButton()
        self.buttonSetEnd.setText('sEn')
        self.buttonSetEnd.setFixedSize(54, 32)
        
        self.layoutPlaybackRange.addWidget(self.buttonSetStart)
        self.layoutPlaybackRange.addWidget(self.sliderPlaybackRange)
        self.layoutPlaybackRange.addWidget(self.buttonSetEnd)
        self.buttonSetStart.clicked.connect(self.set_range)
        self.buttonSetEnd.clicked.connect(self.set_range)
        
        if self.listSongs.is_empty():
            self.playback_enable(False)
        else:
            print('first song loaded:', self.listSongs.playing_song)
            self.load(self.listSongs.playing_song) 
        
    def _play(self):
        mixer.music.play(start=self.start_pos / 1000)
        self.state = PLAYING
        self.buttonPlay.setChecked(True)
        self.buttonPause.setChecked(False)
        self.current_song.buttonPlay.setText(PLAY_LABEL)
        self.current_song.buttonPlay.setChecked(True)
        print('PLAYING...', self.listSongs.playing_song_index, self.current_song.name)
        self.allow_autopos = True
        Thread(target=self._update_playback_slider).start() 
           
    def _pause(self):
        self.start_pos = self.start_pos + mixer.music.get_pos()
        mixer.music.stop()
        self.state = PAUSED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(True)
        self.current_song.buttonPlay.setText(PAUSED_LABEL)
        self.current_song.buttonPlay.setChecked(True)
        print('PAUSED...') 
                
    def _stop(self, event=None):
        print('_STOP --')
        self.start_pos = self.current_song.start_pos
        mixer.music.stop()
        self.state = STOPED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(False)
        self.buttonRepeat.setChecked(self.listSongs.get_selected_song().repeat)
        self.sliderPlaybackPos.setValue(0)
        self.current_song.buttonPlay.setText(PLAY_LABEL)
        self.current_song.buttonPlay.setChecked(False)
        self.change_pos(self.current_song.start_pos)
        print('STOPED...')
        
    def play_pause(self, event=None):
        if self.sender():
            sender = self.sender().parent()
            if type(sender) == SongWidget:
                if sender != self.current_song:
                    self.listSongs.change_row(sender)
                    self.listSongs.set_playing_song(sender)
                    self.eject()
                    self.load(sender)
            elif self.state == STOPED:
                self.eject()
                self.load(self.listSongs.get_selected_song())
        if self.state == STOPED:
            self._play()
            if self.sender() and self.sender().objectName() == 'buttonPause':
                print('sender = pause')
                self._pause()
        else:
            if self.state == PAUSED or not mixer.music.get_busy():
                self._play()
            else:
                self._pause()
            
    def play_next(self, event=None):
        next_song = self.listSongs.get_song('next')
        if next_song:
            self.eject()
            self.load(next_song)
            self._play()   
    
    def play_previous(self, event=None):
        previous_song = self.listSongs.get_song('previous')
        if previous_song:
            self.eject()
            self.load(previous_song)
            
    def deny_autopos(self):
        self.allow_autopos = False
        
    def _update_playback_slider(self,):
        print('UPDATE_PLAYBACK SLIDER --')
        #track_num = self.current_track_num
        song = self.current_song
        current_pos = mixer.music.get_pos()
        playback_pos = self.start_pos + current_pos #дублировано для проверки повтора
        while (mixer.music.get_busy() and 
               self.allow_autopos and
               #track_num == self.current_track_num
               song == self.current_song and
               self.current_song.end_pos >= playback_pos
               ):
            current_pos = mixer.music.get_pos()
            playback_pos = self.start_pos + current_pos
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
        print('autoupdate off')
        if (self.current_song.end_pos - playback_pos < 35 and 
                    self.state == PLAYING):
            self._stop()
            if self.current_song.repeat:
                self._play()
            
    def change_pos(self, pos=None):
        print('CHANGE_POS --')
        if not pos:
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
        if mixer.music.get_busy():
            print('mixer.get_busy --')
            mixer.music.stop()
            mixer.music.play(start=slider_pos / 1000)
        current_min_sec, current_millisec = self.min_sec_from_ms(slider_pos, show_ms=True)
        self.labelCurrentPos.setText(current_min_sec)
        if self.high_acuracy:
            self.labelCurrentPosMs.show()
            self.labelCurrentPosMs.setText(current_millisec)
            self.high_acuracy = False
        self.allow_autopos = True
        if active_threads() < 2:
            Thread(target=self._update_playback_slider).start() 
        print('changing position to', slider_pos / 1000) 
    
    def change_range(self, pbrange=None):
        if not pbrange:
            start_pos, end_pos = self.sliderPlaybackRange.value()
        else:
            start_pos, end_pos = pbrange
        self.current_song.start_pos = start_pos
        self.current_song.end_pos = end_pos
        self.labelEndPos.setText(self.min_sec_from_ms(end_pos))
        if self.sliderPlaybackPos.value() < start_pos:
            self.change_pos(start_pos)
        elif self.sliderPlaybackPos.value() > end_pos:
            self.change_pos(end_pos)
    
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
            self.deny_autopos()
            self.sliderPlaybackPos.setValue(new_slider_pos)
            self.change_pos() 
        
    def step_fforward(self):
        new_slider_pos = self.sliderPlaybackPos.value() + CHANGE_POS_STEP
        if new_slider_pos <= self.current_song.length:
            self.high_acuracy = True
            self.deny_autopos()
            self.sliderPlaybackPos.setValue(new_slider_pos)
            self.change_pos()
    
    def load(self, song):
        if song:
            song.buttonDelete.setDisabled(False)
            self.buttonRepeat.setChecked(song.repeat)
            self.sliderPlaybackPos.setMaximum(song.length)
            self.sliderPlaybackRange.setMaximum(song.length)
            self.sliderPlaybackRange.setValue((song.start_pos, song.end_pos))
            self.current_song = song
            self.change_range((song.start_pos, song.end_pos))
            self.vol_change(song.volume)
            self._stop()
            mixer.music.load(song.path)
        else:
            self.current_song = None
    
    def eject(self):
        if self.current_song:
            self.current_song.normal_mode()
            self.current_song.buttonPlay.setText(PLAY_LABEL)
            self.current_song.buttonPlay.setChecked(False)
            self.current_song.buttonDelete.setDisabled(True)
            self.current_song = None
                    
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
        selected_song = self.listSongs.get_selected_song()
        if self.sender() == selected_song.buttonRepeat:
            selected_song.repeat = not selected_song.repeat
            selected_song.buttonRepeat.setChecked(selected_song.repeat)
            if selected_song == self.current_song:
                self.buttonRepeat.setChecked(selected_song.repeat)
            self.listSongs.set_saved(False)
        elif self.sender() == self.buttonRepeat:
            self.current_song.repeat = not self.current_song.repeat
            self.current_song.buttonRepeat.setChecked(self.current_song.repeat)
            self.buttonRepeat.setChecked(self.current_song.repeat)
            self.listSongs.set_saved(False)
        else:
            sender = self.sender()
            sender.setChecked(not sender.isChecked())
    
    def vol_change(self, vol):
        self.volume = vol
        mixer_volume = vol / 100
        mixer.music.set_volume(mixer_volume)
        self.sliderVol.setValue(self.volume)
        self.current_song.volume = self.volume
    
    def vol_up(self, event=None):
        if self.volume < self.MAX_VOL:
            self.vol_change(self.volume + self.VOLUME_STEP)
            print('VOLUME:', self.volume)
        else:
            print('MAX VOLUME!')
        
    def vol_down(self, event=None):
        if self.volume > self.MIN_VOL:
            self.vol_change(self.volume - self.VOLUME_STEP)
            print('VOLUME:', self.volume)
        else:
            print('MIN VOLUME!')
    
    def playback_enable(self, state=True):
        self.buttonPrevious.setEnabled(state)
        self.buttonStop.setEnabled(state)
        self.buttonPlay.setEnabled(state)
        self.buttonPause.setEnabled(state)
        self.buttonNext.setEnabled(state)
        self.buttonRepeat.setEnabled(state)
            
    def keyPressEvent(self, event):
        print(event.key())
        action = self.controls.get(event.key())
        if action:
            action()

    def closeEvent(self, event):
        self.options['last_playlist_path'] = self.listSongs.save_file_path
        with open(OPTIONS_FILE_PATH, 'w', encoding='utf-8') as options_file:
            json.dump(self.options, options_file, indent=4)
        event.accept()
    
    def qlist_info(self):
        print('INFO:')
        print('current_track_num:', self.listSongs.playing_song_index)
        for index, song in enumerate(self.listSongs.list.get_all_songs()):
            name = 'NONE'
            if song:
                name = song.name
            print(index, name)


def main():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = ClickerPlayerApp() 
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение
    exit()

if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()