# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Main_window.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.

import sys
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic

# from song_item_design import Ui_SongItem
# from main_design import Ui_MainWindow
SONG_ITEM_UI_PATH = 'GUI/songitem.ui'
MAIN_WINDOW_UI_PATH = 'GUI/main_window.ui'

class SongWidget(QtWidgets.QWidget):
    def __init__(self,):
        super().__init__()
        uic.loadUi(SONG_ITEM_UI_PATH, self)
        #self.setupUi(self)


class ClickerPlayerApp(QtWidgets.QMainWindow):
    def __init__(self,):
        super().__init__()
        uic.loadUi(MAIN_WINDOW_UI_PATH, self)
        #self.setupUi(self)
        self.rows = 0
        song = SongWidget()
        self.add_song(song)
        song = SongWidget()
        self.add_song(song)
        
        
    def add_song(self, song):
        item = QtWidgets.QListWidgetItem()
        self.songsList.addItem(item)
        item.setSizeHint(song.sizeHint())
        self.songsList.setItemWidget(item, song)


def main():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = ClickerPlayerApp() 
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение
    exit()

if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()