# -*- coding: utf-8 -*-

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from pygame import mixer
from mutagen.mp3 import MP3 as Mp3
from time import sleep
from threading import Thread
from threading import active_count as active_threads

SONG_ITEM_UI_PATH = 'GUI/songitem.ui'
MAIN_WINDOW_UI_PATH = 'GUI/main_window.ui'

mixer.init()
PLAYBACK_DIR = 'music/'

CHANGE_POS_STEP = 250

STOPED = 0
PLAYING = 1
PAUSED = 2

OK = 1024

PLAY_LABEL = 'P'
PAUSED_LABEL = 'Paused'

LIST_ITEM_HEIGHT = 28
       

class SongWidget(QtWidgets.QWidget):
    def __init__(self, id,
                       path,
                       name,
                       length,
                       ):
        super().__init__()
        self.id = id
        self.path = path
        self.name = name
        self.volume = 50
        self.length = length
        self.start_pos = 0
        self.end_pos = length
        self.repeat = False
        self.fade_in = False
        self.fade_out = False
        self.miuted = False
        
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
        self.normal_mode()
        
    def normal_mode(self):
        self.lineNewSongName.clearFocus()
        self.lineNewSongName.hide()
        self.labelSongName.show()


class SongList(QtWidgets.QListWidget):
    def __init__(self, parent):
        super().__init__()
        #uic.loadUi(SONG_LIST_UI_PATH, self)
        self.player = parent
        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
        self.setAcceptDrops(True)
        self.dragEnabled()
        self.setDragDropMode(QtWidgets.QListWidget.InternalMove)
        self.setSortingEnabled(True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        
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
            print('drop indicator position:', self.dropIndicatorPosition())
            print('from index', from_index)
            print('drop index', drop_index)
            print('current track num =', self.player.current_track_num)
            super().dropEvent(event)
            
        
class ClickerPlayerApp(QtWidgets.QMainWindow):
    HIGH_VOL = 100
    MID_VOL = 50
    LOW_VOL = 0
    def __init__(self, playback_dir):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        
        self.id_source = 0
        
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
            
        first_song = 0
        self.start_pos = 0
        self.last_start_pos = 0
        self.allow_autopos = True
        self.high_acuracy = False
        self.volume = self.MID_VOL
        self.state = STOPED
        
        self.current_track_num = 10000
        self.previous_row = 0
        self.current_song = None
        self.renamed_song = self.current_song
        
        #listSongsWidget = SongList(self)
        self.listSongs = SongList(self)#listSongsWidget.listSongs
        self.layoutSongList.addWidget(self.listSongs)
        self.listSongs.setStyleSheet("QListWidget::item:selected{background:yellow;}")
        self.listSongs.currentRowChanged.connect(self.change_row)
        self.listSongs.itemDoubleClicked.connect(self.rename_song)
        #self.listSongs.itemEntered.connect(self.qlist_info)
        
        self.buttonAddTrack.clicked.connect(self.add_songs)
        
        self.buttonPrevious.clicked.connect(self.play_previous)
        self.buttonStop.clicked.connect(self._stop)
        self.buttonPlay.clicked.connect(self.play_pause)
        self.buttonPause.clicked.connect(self.play_pause)
        self.buttonNext.clicked.connect(self.play_next)
        
        self.buttonRepeat.clicked.connect(self.set_repeat)
        
        self.sliderVol.valueChanged.connect(self.vol_change)
        
        self.sliderPlaybackPos.sliderPressed.connect(self.deny_autopos)
        self.sliderPlaybackPos.sliderReleased.connect(self.change_pos)
        
        self.playback_dir = playback_dir
        files = [f_name for f_name in os.listdir(playback_dir) if not f_name.startswith('.')]
        self.add_songs(files)
        self.change_song(first_song)
   
    def _get_id(self):
        id = self.id_source
        self.id_source += 1
        return id     
        
    def _add_song_widget(self, song_widget):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(QtCore.QSize(1, LIST_ITEM_HEIGHT)) #width based on parent, height = 28
        self.listSongs.addItem(item)
        self.listSongs.setItemWidget(item, song_widget)
        
        #song_widget.buttonPlay.setDisabled(True)
        song_widget.buttonPlay.clicked.connect(self.play_pause)
        song_widget.buttonRepeat.clicked.connect(self.set_repeat)
        song_widget.buttonDelete.setDisabled(True)
        song_widget.buttonDelete.clicked.connect(self._delete_song_widget)
    
    def _delete_song_widget(self):
        confirm_box = QtWidgets.QMessageBox()
        confirm_box.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        confirm_box.setText('Точно удалить?')
        result = confirm_box.exec()
        if result == OK:
            self.listSongs.takeItem(self.current_track_num)
        
    def add_songs(self, filenames=()):
        if not filenames:
            filepaths = QtWidgets.QFileDialog.getOpenFileNames(self, 
                                                    'Добавить дорржки', 
                                                    '.', 
                                                    'Music Files (*.mp3 *.wav)',
                                                    )[0]
            filenames = []
            for filepath in filepaths:
                filedir, filename = os.path.split(filepath)
                filenames.append(filename)
                os.system(f'cp "{filepath}" "{self.playback_dir}"')
            
        for song_filename in filenames:
            path = self.playback_dir + song_filename
            song_info = Mp3(path).info
            length = song_info.length
            length = int(length * 1000) #convert to int milliseconds
            song_widget = SongWidget(id=self._get_id(),
                                     path=path,
                                     name=song_filename,
                                     length=length,
                                     )
            self._add_song_widget(song_widget)
        
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
                    self.change_song(self.get_song_index(sender))
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
            self._play()
        else:
            print('LAST TRACK !')      
    
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
        list_item = self.listSongs.item(song_index)
        self.current_song = self.listSongs.itemWidget(list_item)
        self._stop()
        mixer.music.load(self.current_song.path)
        
        #self.current_song.buttonPlay.setDisabled(False)
        self.current_song.buttonDelete.setDisabled(False)
        self.buttonRepeat.setChecked(self.current_song.repeat)
        self.sliderPlaybackPos.setMaximum(self.current_song.length)
        self.start_pos = self.current_song.start_pos
        self.labelCurrentPos.setText(self.min_sec_from_ms(self.current_song.start_pos))
        self.labelEndPos.setText(self.min_sec_from_ms(self.current_song.end_pos))
            
    def get_song_index(self, selected_song):
        for index, song in enumerate(self.get_all_songs()):
            if song == selected_song:
                return index
                    
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
        selected_song = self.get_song_by_index(self.listSongs.currentRow())
        if self.sender() == selected_song.buttonRepeat:
            selected_song.repeat = not selected_song.repeat
            selected_song.buttonRepeat.setChecked(selected_song.repeat)
            if selected_song == self.current_song:
                self.buttonRepeat.setChecked(selected_song.repeat)
        elif self.sender() == self.buttonRepeat:
            self.current_song.repeat = not self.current_song.repeat
            self.current_song.buttonRepeat.setChecked(self.current_song.repeat)
            self.buttonRepeat.setChecked(self.current_song.repeat)
        else:
            sender = self.sender()
            sender.setChecked(not sender.isChecked())
            return 
    
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
    
    def rename_song(self, list_item=None):
        self.renamed_song = self.listSongs.itemWidget(list_item)
        self.renamed_song.rename()
        
    def change_row(self, row):
        print('CHANGE RAW')
        prev_song = self.get_song_by_index(self.previous_row)
        if prev_song:
            prev_song.buttonDelete.setDisabled(True)
        else:
            print('prev_song widget not detected!')
        self.previous_row = row
        song = self.get_song_by_index(row)
        if song:
            song.buttonDelete.setEnabled(True)
        else:
            print('Song widget not detected!')
        #self.buttonRepeat.setChecked(song.repeat)
        if self.renamed_song:
            self.renamed_song.normal_mode()
        
    def get_all_songs(self):
        songs = []
        for i in range(self.listSongs.count()):
            item = self.listSongs.item(i)
            songs.append(self.listSongs.itemWidget(item))
        return songs
        
    def get_song_by_index(self, index):
        item = self.listSongs.item(index)
        song = self.listSongs.itemWidget(item)
        return song
                
    def keyPressEvent(self, event):
        print(event.key())
        action = self.controls.get(event.key())
        if action:
            action()

    def qlist_info(self):
        for index, song in enumerate(self.get_all_songs()):
            name = 'NONE'
            if song:
                name = song.name
            print(index, name)
            
    # def dragEnterEvent(self, event):
    #     print('Main: ACCEPT')
    #     event.accept()
    #
    # def dropEvent(self, event):
    #     print('SOURCE', event.source())
    #     print('ITEM', event.source().currentItem())
    #     print(dir(event))



def main():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = ClickerPlayerApp(PLAYBACK_DIR) 
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение
    exit()

if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()