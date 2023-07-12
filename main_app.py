# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Main_window.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

import sys
import os
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic

# from song_item_design import Ui_SongItem
# from main_design import Ui_MainWindow
SONG_ITEM_UI_PATH = 'GUI/songitem.ui'
MAIN_WINDOW_UI_PATH = 'GUI/main_window.ui'

PLAYBACK_DIR = 'music/'

class SongWidget(QtWidgets.QWidget):
    def __init__(self, name):
        super().__init__()
        self.name = name
        uic.loadUi(SONG_ITEM_UI_PATH, self)
        self.labelSongName.setText(name)
        self.labelSongName.setToolTip(name)


class ClickerPlayerApp(QtWidgets.QMainWindow):
    MID_VOL = 50
    def __init__(self, playback_dir):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        
        self.playback_dir = playback_dir
        self.files = os.listdir(playback_dir)
        self.songs = []
        for song_name in self.files:
            song = SongWidget(song_name)
            self._add_song(song)
            
        self.current_track = 0
        self.volume = self.MID_VOL
        
        self.listSongs.setStyleSheet("QListWidget::item:selected{background:yellow;}")
        
        
    def _add_song(self, song):
        item = QtWidgets.QListWidgetItem()
        item.setSizeHint(song.sizeHint())
        self.listSongs.addItem(item)
        self.listSongs.setItemWidget(item, song)
        
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


def main():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = ClickerPlayerApp(PLAYBACK_DIR) 
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение
    exit()

if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()