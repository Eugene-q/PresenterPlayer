# -*- coding: utf-8 -*-
'''master VERSION'''

import pdb
import json
import keyboard
import sys
import os
#import codecs
import logging
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from PyQt5.QtCore import QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import assets.icons
from superqt import QRangeSlider
from song_list import SongWidget, SongListWidget, SongList
from constants import *
from constants import set_logger, log_class
from threading import Thread

logging.basicConfig(level=logging.INFO, filename=INFO_LOG_PATH,filemode="w",
                    format="%(asctime)s %(levelname)s\t%(message)s [/%(name)s/%(funcName)s:%(filename)s]")
log = set_logger(__name__)
#logging.error('error!!', exc_info=True)

#sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
#pyrcc5 -o icons.py icons.qrc

@log_class
class OptionsDialog(QtWidgets.QDialog):
    log = set_logger('OptionsDialog')
    
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
            self.log.debug('options set loaded from file')
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
    
@log_class                   
class PlayerApp(QtWidgets.QMainWindow):
    log = set_logger('PlayerApp')
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
        self.log.info(self.__class__.__name__ + ' initialized')
        #self.to_log = to_log
    
    def deck_state_changed(self, state):
        #print('DECK state changed to', state, 'deck position:', self.deck_L.position())
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
        self.log.info(f'PLAYING... {self.list.playing} {song.name}')
           
    def _pause(self):
        self.log.info('PAUSE')
        song = self.list.song(self.list.playing)
        self.play_beep()
        self.deck_L.pause()
        self.state = PAUSED
        self.buttonPlay.setChecked(False)
        self.buttonPause.setChecked(True)
        song.buttonPlay.setIcon(self.PAUSED_ICON)
        song.buttonPlay.setChecked(True)
        self.log.info('PAUSED')
                
    def _stop(self, event=None):
        self.play_beep()
        self.log.info('STOP')
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
        self.log.info('STOPED')
        
    def play_pause(self, event=None, song=None):   
        self.play_beep()
        self.log.info('PLAY/PAUSE')
        if song and song != self.list.song(self.list.playing):
            self._stop()
            self.eject()
            self.list.set_row(song, playing=True)
            #self.load(sender)
        elif not self.enabled:
            self.log.debug('Controls disabled!')
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
        self.log.info('PLAY NEXT')
        self.play_beep()
        state = self.state
        self._stop()
        prev_song = self.list.song(self.list.playing)
        if prev_song.repeat_mode == REPEAT_ONE:
            self.load(prev_song) #загрузка, чтобы сбросить настройки деки
            self._play()
        else:
            next_song = self.get_next_song(state)
            if next_song: #условия разделены по логике для кнопки перемотки и конца трека
                if self.sender() == self.deck_L:
                    if prev_song.repeat_mode != PLAY_ONE:
                        self._play()
                elif self.options.checkBoxAutoplayFforw.isChecked():
                    self._play()
        self.play_next_switch = False
        self.log.debug('play next switched to False')
                
    def get_next_song(self, state):
        repeat_mode = self.repeat_mode
        next_song = None
        song = self.list.get_song('next', state)
        while song and song.muted:
            song = self.list.get_song('next', state)
        if song:
            next_song = song
        elif repeat_mode == REPEAT_ALL:
            self.list.playing = 0
            self.list.set_current_row(0)
            song = self.list.song(0)
            while song and song.muted:
                song = self.list.get_song('next', state)
            next_song = song
        return next_song
    
    def play_previous(self, event=None):
        self.play_beep()
        state = self.state
        self._stop()
        previous_song = self.list.get_song('previous', state)
        while previous_song and previous_song.muted:
            previous_song = self.list.get_song('previous', state)
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
        self.log.debug('volume automation off')
    
    def start_volume_update(self):
        if self.volume_update_thread:
            if self.volume_update_thread.is_alive():
                self.allow_automations_update(playback=None, volume=False)
        song =  self.list.song(self.list.playing)
        playback_pos = self.deck_L.position() #дублировано для проверки повтора
        #to_end_delta = song.end_pos - playback_pos #дублировано для проверки перехода
        self.log.debug('START VOLUME AUTOMATION')
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
        #print('CHANGE_POS: changed to', slider_pos)
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
        if song:
            self.waveform = song.waveform
            self.resizeEvent(QtGui.QResizeEvent)
            if not song.muted:
                content = QMediaContent(QUrl.fromLocalFile(song.path))
                self.deck_L.setMedia(content)
                self.deck_L.setPosition(song.start_pos)
                #print('start pos:', song.start_pos)
                song.buttonDelete.setEnabled(True)
                self.enable()#just_playback=True)
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
                self.update()
            else:
                self.log.debug('song not LOADED because it is muted')
        else:
             self.log.error(f'No song to load! Current song: {self.list.song(self.list.selected)}')
        return f'{song.name[:20]}'
    
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
        repeat_mode = (self.repeat_mode + 1) % 3
        if repeat_mode == PLAY_ONE:
            for song in self.list.list.get_all_songs():
                song.set_repeat_to(PLAY_ONE)
        elif self.prev_repeat_mode == PLAY_ONE:
            for song in self.list.list.get_all_songs():
                if song.repeat_mode == PLAY_ONE:
                    song.set_repeat_to(AS_LIST)
        self.set_repeat_to(repeat_mode)
        self.prev_repeat_mode = self.repeat_mode
        #self.list.save()
    
    def set_repeat_to(self, mode):
        self.log.debug(f'SET REPEAT TO {mode}')
        mode_settings = self.REPEAT_MODES.get(mode)
        self.repeat_mode = mode
        self.buttonRepeat.setChecked(mode_settings.get('checked'))
        self.buttonRepeat.setIcon(mode_settings.get('icon'))
    
    def master_vol_change(self, vol):
        self.master_volume = vol
        self.sliderMasterVol.setValue(self.master_volume)
        self.apply_volume()
            
    def song_vol_change(self, vol, move_slider=False):
        self.log.info('SONG VOLUME CHANGE')
        self.song_volume = vol
        if move_slider: #слайдер вызывает этот же метод при перемещении, если его позиция изменилась
            self.sliderSongVol.setValue(self.song_volume)
        self.apply_volume()
        self.log.debug(f'changed to {vol}')
        
    def song_vol_write(self,):
        self.log.debug(f'song vol writed: {self.song_volume}')
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
            self.log.info('MAX VOLUME!')
        else:
            self.master_vol_change(next_master_volume)
        self.log.info(f'VOLUME: {self.master_volume}')
        
    def vol_down(self, event=None):
        next_master_volume = self.master_volume - self.VOLUME_STEP
        if next_master_volume < self.MIN_VOL:
            self.master_vol_change(self.MIN_VOL)
            self.log.info('MIN VOLUME!')
        else:
            self.master_vol_change(next_master_volume)
        self.log.info(f'VOLUME: {self.master_volume}')
    
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
        self.log.debug(f'{fade_in_raito} {fade_out_raito}')
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
        self.log.debug(f'Enable: {state}')
        #self.log.debug(f'Sender: {self.sender()}')
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
        self.log.info('App closing...')
        self.options.save()
        self.deny_playback_automation()
        self.deny_volume_automation()
        self.deck_L.stop()
        self.list.save(check_filenames=False)
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
    print('* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *')
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    app.setWindowIcon(QtGui.QIcon(os.path.join(BASE_DIR, 'app_icon.icns')))
    log.info('App starting...')
    window = PlayerApp() 
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение
    exit()

if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()