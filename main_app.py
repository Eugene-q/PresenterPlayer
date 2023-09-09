# -*- coding: utf-8 -*-

import json
import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from pygame import mixer
from mutagen.mp3 import MP3
from mutagen.wave import WAVE
from shutil import copyfile, rmtree
from time import sleep
from threading import Thread
from threading import active_count as active_threads

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


class SongList(QtWidgets.QListWidget):
    def __init__(self, parent, initial_save_file_path):
        super().__init__()
        
        #GUI settings
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAcceptDrops(True)
        self.dragEnabled()
        self.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        self.setSortingEnabled(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setStyleSheet("QListWidget::item:selected{background:yellow;}")
        
        self.currentRowChanged.connect(self.change_row)
        self.itemDoubleClicked.connect(self.rename_song)
        
        self.player = parent
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
        if drop_index != from_index: #to fix drop bag
            active_song_index = self.player.current_track_num
            print('active song index', active_song_index)
            if active_song_index == from_index:
                self.player.current_track_num = drop_index
            elif from_index < active_song_index and drop_index >= active_song_index:
                self.player.current_track_num -= 1
            elif from_index > active_song_index and drop_index <= active_song_index:
                self.player.current_track_num += 1
            self.set_saved(False)
            print('drop indicator position:', self.dropIndicatorPosition())
            print('from index', from_index)
            print('drop index', drop_index)
            print('current track num =', self.player.current_track_num)
            super().dropEvent(event)
    
    def change_row(self, row):
        print('CHANGE ROW')
        prev_song = self.get_song_by_index(self.previous_row)
        if prev_song:
            prev_song.buttonDelete.setDisabled(True)
        else:
            print('prev_song widget not detected!')
        self.previous_row = row
        song = self.get_song_by_index(row)
        if song:
            song.buttonDelete.setEnabled(True)
            if song == self.player.current_song:
                self.player.buttonRepeat.setChecked(song.repeat)
            if self.player.state is STOPED:
                self.player.change_song(row)
        else:
            print('Song widget not detected!') 
        if self.renamed_song:
            self.renamed_song.normal_mode()
        self.normal_mode()
    
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
    
    def _get_id(self):   # TODO Переписать как генератор
        id = self.id_source
        self.id_source += 1
        return id
        
    def _add_song_widget(self, song_widget):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(1, LIST_ITEM_HEIGHT)) #width based on parent, height = 28
        self.addItem(item)
        self.setItemWidget(item, song_widget)
        self.saved = False
        
        #song_widget.buttonPlay.setDisabled(True)
        song_widget.buttonPlay.clicked.connect(self.player.play_pause)
        song_widget.buttonRepeat.clicked.connect(self.player.set_repeat)
        song_widget.buttonDelete.setDisabled(True)
        song_widget.buttonDelete.clicked.connect(self._delete_song_widget)
    
    def _delete_song_widget(self):
        delete_index = self.currentRow()
        if delete_index == self.player.current_track_num and self.player.state is not STOPED:
            self.show_message_box(DELETE_PLAYING_WARNING, cancel=False)
        elif self.show_message_box('Точно удалить?') == OK:
                if delete_index < self.player.current_track_num:
                    self.player.current_track_num -= 1
                self.takeItem(delete_index)
                # if self.count() < 1:
                #     self.player.buttonSaveList.setDisabled(True)
                self.set_saved(False)
                    
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
                self._add_song_widget(song_widget)
        else:
            if not filenames:
                filepaths = QtWidgets.QFileDialog.getOpenFileNames(self, 
                                                        'Добавить дорржки', 
                                                        '.', 
                                                        'Music Files (*.mp3 *.wav)',
                                                        )[0]
                filenames = []
                current_playback_filenames = self.get_playback_filenames()
                print('Playback filenames:', current_playback_filenames)
                for filepath in filepaths:
                    filedir, filename = os.path.split(filepath)
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
                    print('Unsupported sound file!')
                length = song_info.length
                length = int(length * 1000) #convert to int milliseconds
                song_widget = SongWidget(parent=self,
                                         id=self._get_id(),
                                         path=song_file_path,
                                         name=song_name,
                                         file_type=file_type,
                                         length=length,
                                         )
                self._add_song_widget(song_widget)
        self.set_saved(False)
        self.player.playback_enable(True)
        self.player.current_song = None
        if hasattr(self.player, 'listSongs'):
            self.player.change_song(0)
    
    def rename_song(self, list_item=None):
        self.renamed_song = self.itemWidget(list_item)
        self.renamed_song.rename()
        
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
    
    def get_playback_filenames(self):
        return [f_name.strip() for f_name in os.listdir(self.playback_dir
                                    ) if not f_name.startswith('.')]
    
    def get_playback_dir_path(self, list_file_path):
        dirname, filename = os.path.split(list_file_path)
        return os.path.join(dirname, filename.partition('.')[0] + '_music')
            
    def set_saved(self, saved=True):
        self.saved = saved
        if saved:
            self.player.labelSaveSign.setText('')
            list_name = os.path.basename(self.save_file_path).partition('.')[0]
            print('list name for button:', list_name)
            self.player.buttonSongListHeader.setText(list_name)
            self.player.buttonSongListHeader.setToolTip(list_name)
            self.player.buttonSaveList.setDisabled(True)
        else:
            self.player.labelSaveSign.setText('*')
            self.player.buttonSaveList.setEnabled(True)
                
    def save(self):
        if not self.saved:
            songs_info = []
            for song in self.get_all_songs():
                songs_info.append(self.get_song_info(song))
            #print('Save file path:', self.save_file_path)
            with open(self.save_file_path, 'w') as save_file:
                json.dump(list(reversed(songs_info)), save_file, indent=4)
            song_filenames = [os.path.basename(song.get('path')) for song in songs_info]
            for filename in self.get_playback_filenames():
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
            print('NEW MUSIC DIR:', music_dir_path)
            if save_file_path:
                songs_info = []
                if os.path.exists(music_dir_path):
                    rmtree(music_dir_path)
                os.mkdir(music_dir_path)
                self.playback_dir = music_dir_path
                for song in self.get_all_songs():
                    new_song_path = os.path.join(music_dir_path, song.name+'.'+song.file_type)
                    copyfile(song.path, new_song_path)
                    print(f'copied from {song.path} to {new_song_path}')
                    song.path = new_song_path
                    songs_info.append(self.get_song_info(song))
                with open(save_file_path, 'w') as save_file:
                    print('save file opened', save_file)
                    json.dump(list(reversed(songs_info)), save_file, indent=4)
                self.set_saved()
                new_list_name = os.path.basename(save_file_path).partition('.')[0]
                self.player.buttonSongListHeader.setText(new_list_name)
                self.player.buttonSongListHeader.setToolTip(new_list_name)
        self.save_file_path = save_file_path
                      
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
            print('Load file path:', load_file_path)
            with open(load_file_path, 'r') as load_file:
                songs_info = json.load(load_file)
            #if songs_info:
            if self.count() > 0:
                pass
            self.clear()
            self.player.current_song = None
            if songs_info:
                self.add_songs(songs_info=songs_info)
                if hasattr(self.player, 'listSongs'):
                    self.player.change_song(0)
            self.save_file_path = load_file_path
            self.playback_dir = self.get_playback_dir_path(load_file_path)
            self.set_saved()
            # else:
#                 print('no songs_info !')

    def clear(self):
        if not self.saved:
            if self.show_message_box(CLEAR_WARNING) != OK:
                return
        self.player.playback_enable(False)
        super().clear()
        self.set_saved(True)
    
    def rename_mode(self):
        self.player.buttonSongListHeader.hide()
        self.player.lineSongListHeader.show()
        self.player.lineSongListHeader.setText(self.player.buttonSongListHeader.text())
        self.player.lineSongListHeader.selectAll()
        self.player.lineSongListHeader.setFocus()
    
    def save_list_name(self):
        new_name = self.player.lineSongListHeader.text()
        new_save_file_path = os.path.join(os.path.dirname(self.save_file_path),
                                            new_name+SONG_LIST_EXTENSION)
        new_save_file_path = os.path.abspath(new_save_file_path) 
        old_save_file_path = self.save_file_path                                   
        print('OLD PATH:', self.save_file_path)
        print('NEW PATH:', new_save_file_path)
        self.save_as(new_save_file_path)
        os.remove(old_save_file_path)
        rmtree(self.get_playback_dir_path(old_save_file_path))
        self.normal_mode()
        self.player.buttonSongListHeader.setText(new_name)
        self.player.buttonSongListHeader.setToolTip(new_name)
        
    def normal_mode(self):
        self.player.buttonSongListHeader.show()
        self.player.lineSongListHeader.hide()
        self.player.lineSongListHeader.clearFocus()
        
            
        
class ClickerPlayerApp(QtWidgets.QMainWindow):
    HIGH_VOL = 100
    MID_VOL = 50
    LOW_VOL = 0
    def __init__(self,):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        
        self.controls = {QtCore.Qt.Key_Escape: self.play_next,
                         #QtCore.Qt.Key_Shift: self.play_next,
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
        self.last_start_pos = 0
        self.allow_autopos = True
        self.high_acuracy = False
        self.volume = self.MID_VOL
        self.state = STOPED
        
        self.current_track_num = 10000
        self.current_song = None
        
        self.listSongs = SongList(self, self.options.get('last_playlist_path'))
        self.layoutSongList.addWidget(self.listSongs)
        
        self.lineSongListHeader.hide()
        self.lineSongListHeader.returnPressed.connect(self.listSongs.save_list_name)
        self.buttonSongListHeader.clicked.connect(self.listSongs.rename_mode)
        self.buttonSongListHeader.setToolTip(self.buttonSongListHeader.text())
        self.buttonAddTrack.clicked.connect(self.listSongs.add_songs)
        
        self.buttonSaveList.clicked.connect(self.listSongs.save)
        self.buttonSaveListAs.clicked.connect(self.listSongs.save_as)
        self.buttonLoadList.clicked.connect(self.listSongs.load)
        self.buttonClearList.clicked.connect(self.listSongs.clear)
        
        self.buttonPrevious.clicked.connect(self.play_previous)
        self.buttonStop.clicked.connect(self._stop)
        self.buttonPlay.clicked.connect(self.play_pause)
        self.buttonPause.clicked.connect(self.play_pause)
        self.buttonNext.clicked.connect(self.play_next)
        
        self.buttonRepeat.clicked.connect(self.set_repeat)
        
        self.sliderVol.valueChanged.connect(self.vol_change)
        
        self.sliderPlaybackPos.sliderPressed.connect(self.deny_autopos)
        self.sliderPlaybackPos.sliderReleased.connect(self.change_pos)
        
        first_song = self.listSongs.get_song_by_index(0)
        if first_song:
            self.change_song(0) 
        else:
            self.playback_enable(False) 
        
    def _play(self):
        mixer.music.play(start=self.start_pos / 1000)
        self.state = PLAYING
        self.buttonPlay.setChecked(True)
        self.buttonPause.setChecked(False)
        self.current_song.buttonPlay.setText(PLAY_LABEL)
        self.current_song.buttonPlay.setChecked(True)
        print('PLAYING...', self.current_track_num, self.current_song.name)
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
        self.start_pos = self.last_start_pos = 0
        mixer.music.stop()
        self.state = STOPED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(False)
        self.sliderPlaybackPos.setValue(0)
        self.current_song.buttonPlay.setText(PLAY_LABEL)
        self.current_song.buttonPlay.setChecked(False)
        self.change_pos()
        print('STOPED...')
        
    def play_pause(self, event=None):
        if self.sender():
            sender = self.sender().parent()
            if type(sender) == SongWidget:
                if sender != self.current_song:
                    self.change_song(self.listSongs.get_song_index(sender))
            elif self.state == STOPED:
                self.change_song(self.listSongs.currentRow())
        if self.state == STOPED:
            #self.change_song(self.current_track_num)
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
        if self.state == PLAYING or self.state == PAUSED:
            current_track_num = self.current_track_num
        else:
            current_track_num = self.listSongs.currentRow()
        if current_track_num + 1 < self.listSongs.count():
            next_track_num = current_track_num + 1
            self.listSongs.setCurrentRow(next_track_num)
            self.change_song(next_track_num)
            self.current_track_num = next_track_num
            self._play()
        else:
            print('LAST TRACK !')  
        print('NEXT: current track:', self.current_track_num)    
    
    def play_previous(self, event=None):
        if self.current_track_num > 0:
            next_track_num = self.current_track_num - 1
            self.listSongs.setCurrentRow(next_track_num)
            self.change_song(next_track_num)
            self._play()
            self._pause()
        else:
            print('FIRST TRACK !')
            
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
               song == self.current_song
               ):
            current_pos = mixer.music.get_pos()
            playback_pos = self.start_pos + current_pos
            if playback_pos % 250 < 20:
                self.sliderPlaybackPos.setValue(playback_pos)
            if playback_pos % 1000 < 20:
                self.labelCurrentPos.setText(self.min_sec_from_ms(playback_pos))
            sleep(0.01)
        # print('mixer get busy:', mixer.music.get_busy())
        # print('autopos:', self.allow_autopos)
        # print('track:', track_num == self.current_track_num)
        print('autoupdate off')
        if (abs(self.current_song.length - playback_pos) < 35 and 
                    self.state == PLAYING):
            self._stop()
            if self.current_song.repeat:
                self._play()
            
    def change_pos(self):
        print('CHANGE_POS --')
        slider_pos = self.sliderPlaybackPos.value()
        self.start_pos = slider_pos
        if mixer.music.get_busy():
            print('mixer.get_busy --')
            mixer.music.stop()
            mixer.music.play(start=slider_pos / 1000)
        self.labelCurrentPos.setText(self.min_sec_from_ms(slider_pos))
        self.allow_autopos = True
        if active_threads() < 2:
            Thread(target=self._update_playback_slider).start() 
        print('changing position to', slider_pos / 1000) 
        
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
                     
    def change_song(self, song_index):
        print('CHANGE_SONG --')
        # if song_index != self.current_track_num:
        #     print('new song num')
        if self.current_song:
            self.current_song.normal_mode()
            self.current_song.buttonPlay.setText(PLAY_LABEL)
            self.current_song.buttonPlay.setChecked(False)
            self.current_song.buttonDelete.setDisabled(True)
            self.previous_row = self.listSongs.currentRow()
        self.listSongs.setCurrentRow(song_index)
        self.current_track_num = song_index
        self.current_song = self.listSongs.get_song_by_index(song_index)
        self._stop()
        mixer.music.load(self.current_song.path)
        
        #self.current_song.buttonPlay.setDisabled(False)
        self.current_song.buttonDelete.setDisabled(False)
        self.buttonRepeat.setChecked(self.current_song.repeat)
        self.sliderPlaybackPos.setMaximum(self.current_song.length)
        self.start_pos = self.current_song.start_pos
        self.labelCurrentPos.setText(self.min_sec_from_ms(self.current_song.start_pos))
        self.labelEndPos.setText(self.min_sec_from_ms(self.current_song.end_pos))
                    
    def min_sec_from_ms(self, milliseconds):
        sec_float = milliseconds / 1000
        sec_int = int(sec_float)
        hundr_sec = int((sec_float - sec_int) * 100)
        minutes = sec_int // 60
        sec = sec_int % 60
        if self.high_acuracy:
            result = f'{minutes :02.0f}:{sec :02.0f}:{hundr_sec :02.0f}'
        else:
            result = f'{minutes :02.0f}:{sec :02.0f}'
        self.high_acuracy = False
        return result
    
    def set_repeat(self):
        selected_song = self.listSongs.get_song_by_index(self.listSongs.currentRow())
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
    
    def vol_up(self, event=None):
        if self.volume < self.HIGH_VOL:
            self.volume += 10
            self.vol_change(self.volume)
            print('VOLUME:', self.volume)
        else:
            print('MAX VOLUME!')
        
    def vol_down(self, event=None):
        if self.volume > self.LOW_VOL:
            self.volume -= 10
            self.vol_change(self.volume)
            print('VOLUME:', self.volume)
        else:
            print('MIN VOLUME!')
    
    def playback_enable(self, state):
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
        print('current_track_num:', self.current_track_num)
        for index, song in enumerate(self.listSongs.get_all_songs()):
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