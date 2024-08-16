import audioread
import inspect
from collections import deque
from constants import *
from constants import set_logger, log_class
import json 
import logging
import os
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5 import uic
from PyQt5.QtCore import QCoreApplication


@log_class
class SongWidget(QtWidgets.QWidget):
    log = set_logger('SongWidget')
    def __init__(self, parent,
                       id,
                       name,
                       length,
                       file_name,
                       volume=100,
                       start_pos=0,
                       end_pos=0,
                       repeat_mode=AS_LIST,
                       fade_range=(0, 0),
                       muted=False,
                       waveform=[]
                       ):
        super().__init__()
        
        self.log = logging.getLogger(self.__class__.__name__)
        self.log.setLevel(LOGGING_LEVEL)
        self.log.addHandler(ERROR_HANDLER)
        self.log.addHandler(DEBUG_HANDLER)
        
        self.id = id
        self.name = name
        self.file_name = file_name
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
    
    def play(self, event=None):
        self.song_list.player.play_pause(song=self)
        
    def mute(self, event=None):
        self.muted = not self.muted
        self.buttonMute.setChecked(self.muted)
        self.song_list.mute_song(self)
        
    def duplicate(self, event=None):
        self.song_list.duplicate_song_widget(self)
        
    def delete_from_list(self, event=None):
        self.song_list.delete_song_widget(self)
        
    def set_repeat(self, event=None):
        self.repeat_mode = (self.repeat_mode - 1) % 3 + 2
        if self.song_list.player.repeat_mode == PLAY_ONE and self.repeat_mode == AS_LIST:
            self.repeat_mode = (self.repeat_mode - 1) % 3 + 2
        print('Repeat mode sets...', self.repeat_mode)
        self.set_repeat_to(self.repeat_mode)
        
    def set_repeat_to(self, mode):
        self.log.debug(f'SET REPEAT TO {mode}')
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
        new_name = self.lineNewSongName.text()
        if self.song_list.player.options.checkBoxHardLinkFileName.isChecked():
            names_in_list = [info.get('name') for info in self.song_list.list.get_all_songs(info=True)]
            names_in_list.remove(self.name)
            if new_name in names_in_list:
                show_message_box(SONG_NAME_EXISTS_WARNING, cancel_text='', log=self.log)
                return
            else:
                self.name = new_name
                self.update_filename()
        self.name = new_name
        self.labelSongName.setText(self.name)
        self.song_list.save(check_filenames=False)
        self.normal_mode()
        
    def normal_mode(self):
        self.lineNewSongName.clearFocus()
        self.lineNewSongName.hide()
        self.labelSongName.show()
        self.song_list.player.enable_controls()
    
    def update_filename(self):
        old_name, filetype = os.path.splitext(self.file_name)
        if old_name != self.name:
            new_filename = self.name + filetype
            old_path = os.path.join(self.song_list.playback_dir, self.file_name)
            new_path = os.path.join(self.song_list.playback_dir, new_filename)
            copy_file(old_path, new_path)
            used_filenames = [song.file_name for song in self.song_list.list.get_all_songs()]
            used_filenames.remove(self.file_name)
            if self.file_name not in used_filenames:
                remove_file(old_path)
            self.file_name = new_filename
    
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
    
    def __str__(self):
        return f'SongWidget {self.name}'


@log_class
class SongListWidget(QtWidgets.QWidget):
    log = set_logger('SongListWidget')
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
        if filenames:
            self.log.info('add songs by filenames')
        list_was_empty = self.is_empty() 
        if songs_info:                   # Добавление песен из загруженного списка
            self.log.info('add songs from songs_info')
            for info in songs_info:
                song_widget = SongWidget(parent=self,
                                        id=info.get('id'),
                                        name=info.get('name'),
                                        file_name=info.get('file_name'),
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
                self.log.info('add songs selected by user')
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
                        #self.log.debug(f'filename {filename} is not in:')
                        #for f_n in current_playback_filenames:
                        #    self.log.debug(f'{f_n}')
                        copy_file(filepath, 
                                  os.path.join(self.playback_dir, filename),
                                  self.log)
            new_songs_info = []
            for song_filename in filenames:
                song_file_path = os.path.join(self.playback_dir, song_filename)
                try:
                    with audioread.audio_open(song_file_path) as audio_file:
                        duration = audio_file.duration
                        length = int(duration * 1000)
                        song_name, file_type = os.path.splitext(song_filename)
                        song_widget = SongWidget(parent=self,
                                                 id=self.get_id(),
                                                 name=song_name,
                                                 file_name=song_filename,
                                                 length=length,
                                                 waveform=[]
                                                 )
                        self.add_song_widget(song_widget)
                        new_songs_info.append(self.list.get_song_info(song_widget))
                except audioread.exceptions.NoBackendError as e:
                    show_message_box(f'Не удаётся открыть файл! \n{song_filename}', cancel_text='')
                    self.log.error(f'Не удаётся открыть файл! {song_file_path}', exc_info=True)
                    continue        
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
            self.log.debug(f'getting waveform. {info.get("name")}')
            self.player.progressBuildWaveform.setValue(0)
            self.player.progressBuildWaveform.show()
            try:
                song_path = os.path.join(self.playback_dir, info.get('file_name'))
                with audioread.audio_open(song_path) as audio_file:
                    #print('Unsupported sound file!')#TODO Сделать окно предупреждения
                    channels = audio_file.channels 
                    samplerate = audio_file.samplerate
                    duration = audio_file.duration
                    self.log.debug(f'{channels}, {samplerate}, {duration}')
                    #print('total samples:', samplerate * duration)
                    width = (BASE_WAVEFORM_DISPLAY_WIDTH - PLAYBACK_SLIDER_WIDTH_OFFSET - 
                                    PLAYBACK_SLIDER_WAVEFORM_OFFSET)
                    self.player.progressBuildWaveform.setMaximum(width)
                    total_samples = int(channels * samplerate * duration)
                    #step = total_samples // width
                    read_pos = 0
                    samples = []
                    first_buf = True
                    for buf in audio_file:
                        buf_int = memoryview(buf).cast('h')
                        if first_buf:
                            buf_size = len(buf_int)
                            total_buffers = total_samples // buf_size
                            buffers_per_step = total_buffers / width - 1
                            buf_count = buffers_per_step
                            self.log.debug(f'buf_size:{buf_size} t_samples:{total_samples} t_buff:{total_buffers}')
                            self.log.debug(f'buf_per_step:{buffers_per_step} width:{width}')
                            first_buf = False
                        if buf_count < 1:
                            QCoreApplication.processEvents()
                            byte_L = buf_int[0]
                            byte_R = buf_int[1]
                            sample = max((abs(byte_L), abs(byte_R)))
                            samples.append(sample)
                            buf_count += buffers_per_step
                            val = self.player.progressBuildWaveform.value()
                            #self.log.debug(f'progress value {val} of {width}')
                            self.player.progressBuildWaveform.setValue(val + 1)
                        else:
                            buf_count -= 1
                    self.log.debug(f'samples extracted!')
                    waveform = []
                    frame = deque(maxlen=WAVEFORM_AVERAGING_FRAME_WIDTH)
                    max_sample = max(samples)
                    self.log.debug(f'Max sample: {max_sample}')
                    for sample in samples:
                        sample = int(self.scale_number(sample, 0, WAVEFORM_HEIGHT, 0, max_sample))
                        frame.append(sample)
                        if len(frame) >= WAVEFORM_AVERAGING_FRAME_WIDTH:
                            sample_averaged = int(sum(frame) / WAVEFORM_AVERAGING_FRAME_WIDTH)
                            waveform.append(sample_averaged)
                    self.log.debug(f'Max waveform: {max(waveform)}')
                    self.list.set_waveform(info.get('id'), waveform)
            except Exception:
                self.log.error('Waveform error!', exc_info=True)
                show_message_box(WAVEFORM_ERROR_WARNING, cancel_text='')
            self.player.progressBuildWaveform.hide()
    
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
        song_name = parent_song.name
        if self.options.checkBoxHardLinkFileName.isChecked():
            all_songs = self.list.get_all_songs()
            song_file_name, file_type = os.path.splitext(parent_song.file_name)
            print('song_file_name:', song_file_name)
            all_songs_names = [s.name for s in all_songs]
            all_songs_names.remove(song_name)
            while song_name in all_songs_names:
                song_name += '-копия'
            all_songs_file_names = [s.file_name for s in all_songs]
            print('all filenames:', all_songs_file_names)
            all_songs_file_names.remove(song_file_name + file_type)
            while (song_name + file_type) in all_songs_file_names:
                song_name += '-копия'
            song_path = os.path.join(self.playback_dir, song_name+file_type)
            while os.path.exists(song_path):        
                song_name += '-копия'
                song_path = os.path.join(self.playback_dir, song_name+file_type)
            parent_song_path = os.path.join(self.playback_dir, parent_song.file_name)
            copy_file(parent_song_path, song_path)
            file_name = song_name + file_type
        else:
            file_name = parent_song.file_name
        song_widget = SongWidget(parent=self,
                                id=self.get_id(),
                                name=song_name,
                                file_name=file_name,
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
    
    def delete_song_widget(self, song, silent=False):
        self.log.info(f'{song.name}')
        delete_index = self.list.get_song_index(song)
        if delete_index == self.playing and self.player.state is not STOPED:
            show_message_box(DELETE_PLAYING_WARNING, cancel_text='')
        elif silent or show_message_box(DELETE_SONG_WARNING) == OK:
                if delete_index < self.playing:
                    self.playing -= 1
                self.list.takeItem(delete_index)
                if delete_index <= self.list.count() - 1:
                    self.selected = delete_index
                else:
                    self.selected = delete_index - 1
                self.save(check_filenames=False)
                if self.is_empty():
                    self.player.eject()
                    
    def set_unique_names(self):
        all_songs = self.list.get_all_songs()
        for song in all_songs:
            unique_name = song.name
            song_file_name, file_type = os.path.splitext(song.file_name)
            if unique_name != song_file_name:
                self.duplicate_song_widget(song)
                self.delete_song_widget(song, silent=True)
    
    def save_list_name(self):
        delete_old_list = self.options.checkBoxRenameDeleteOldList.isChecked()
        new_name = self.lineListHeader.text()
        new_file_name = new_name + SONG_LIST_EXTENSION
        save_dir = os.path.dirname(self.save_file_path)
        if (not self.find_files((new_file_name,), save_dir) or
                    show_message_box(LIST_FILE_EXISTS_WARNING.format(new_name), 
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
                if (not self.new_list_created and
                        self.options.checkBoxRenameDeleteOldList.isChecked()
                        ):
                    remove_file(old_save_file_path, self.log)
                    self.player.eject() 
                    remove_dir(self.get_playback_dir_path(old_save_file_path))
                else:
                    self.buttonListHeader.setText(new_name)
                    self.buttonListHeader.setToolTip(new_name)
        self.normal_mode()
        self.new_list_created = False
        if not self.is_empty():
            self.player.load(self.song(self.playing))
        else:
            self.player.enable(False)
    
    def new_list(self, event=None):
        if show_message_box(NEW_LIST_WARNING) == OK:
            self.save(check_filenames=False)
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
        self.log.debug(f'Saving... check_filenames={check_filenames}')
        self.log.debug(f'silent={silent}')
        self.log.info(f'{self.save_file_path}')
        list_name = os.path.basename(self.save_file_path).partition('.')[0]
        self.buttonListHeader.setText(list_name)
        self.buttonListHeader.setToolTip(list_name)
        songs_info = []
        short_names = []
        for song_info in self.list.get_all_songs(info=True):
            short_names.append(song_info.get('name')[:4])
            songs_info.append(song_info)
        self.log.debug(f'saved: {short_names}')
        #print('Save file path:', self.save_file_path)
        try:
            with open(self.save_file_path, 'w') as save_file:
                json.dump(songs_info, save_file, indent=4)
        except Exception as e:
            self.log.error('Ошибка сохранения файла списка!', exc_info=True)
            self.log.error(f'songlist file path: {self.save_file_path}')
            self.log.error(f'not saved files: {short_names}')
            show_message_box(SONG_LIST_SAVING_ERROR_WARNING.format(e), cancel_text='')
        if check_filenames:
            self.log.debug('checking filenames...')
            song_filenames = [song_info.get('file_name') for song_info in songs_info]
            filenames_not_in_list = self.find_files(file_list=song_filenames, 
                                            search_dir=self.playback_dir,
                                            search_in_list=True,
                                            not_found=True)
            silent_mode = 'remove'
            for filename in filenames_not_in_list:
                if silent:
                    if silent_mode == 'remove':
                        message_result = OK_CHECKED
                    else:
                        message_result = MIDDLE_CHECKED
                else:
                    warning = SOURCE_DELETE_WARNING.format(filename.partition('.')[0])
                    message_result = show_message_box(warning, 
                                                    ok_text='Удалить',
                                                    cancel_text='Оставить',
                                                    middle_text='Вернуть в список',
                                                    checkbox_text='Применить ко всем')
                if message_result == OK or message_result == OK_CHECKED:
                    if remove_file(os.path.join(self.playback_dir, filename), self.log):
                        self.log.debug(f'REMOVED: {filename}')   
                    if message_result == OK_CHECKED:
                        silent_mode = 'remove'
                        silent = True
                elif message_result == MIDDLE or message_result == MIDDLE_CHECKED:
                    self.add_songs(filenames=[filename,])
                    if message_result == MIDDLE_CHECKED:
                        silent_mode = 'return'
                        silent = True
                elif message_result == CANCEL_CHECKED:
                    break
    
    def save_as(self, save_file_path='', blank=False):
        if not save_file_path:
            save_file_path = QtWidgets.QFileDialog.getSaveFileName(self, 'Файл сохранения',
                                     os.path.join('.', self.options.save_dir()), 'SongList File (*.sl)')[0]
            self.player.setFocus()
        if save_file_path and save_file_path != self.save_file_path:
            new_playback_dir_path = self.get_playback_dir_path(save_file_path)
            if os.path.exists(new_playback_dir_path):
                    remove_dir(new_playback_dir_path)
            os.mkdir(new_playback_dir_path)
            if not blank:
                for song in self.list.get_all_songs():
                    old_song_path = os.path.join(self.playback_dir, song.file_name)
                    new_song_path = os.path.join(new_playback_dir_path, song.file_name)
                    copy_file(old_song_path, new_song_path, self.log)
            self.playback_dir = new_playback_dir_path
            self.save_file_path = save_file_path
        self.save()
                 
    def load(self, load_file_path=''):
        if self.save_file_path:
            self.log.info(f'save previous list')
            self.save(check_filenames=False)
        if not load_file_path:
            self.log.debug('select songlist file')
            load_file_path = QtWidgets.QFileDialog.getOpenFileName(self, 
                                                    'Загрузка списка песен', 
                                                    self.options.save_dir(), 
                                                    F'SongList File (*{SONG_LIST_EXTENSION})',
                                                    )[0]
            self.log.info(f'selected file to load: {load_file_path}')
        if load_file_path and self.project_is_valid(load_file_path):
            songs_info = []
            try: 
                with open(load_file_path, 'r') as load_file:
                    songs_info = json.load(load_file)
            except FileNotFoundError:
                self.log.error('Файл списка не найден!', exc_info=True)
                show_message_box(LIST_LOADING_ERROR)
            except PermissionError:
                self.log.error('Доступ к файлу списка запрещён!', exc_info=True)
                show_message_box(LIST_LOADING_ERROR)
            else:
                self.save_file_path = load_file_path
                self.playback_dir = self.get_playback_dir_path(load_file_path)
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
            self.player.set_repeat_to(PLAY_ALL)
            self.log.debug('saving loaded list...')
            self.save() #вызывается чтобы проверить лишние файлы в папке списка.
        self.player.setFocus()
            
    def clear(self, silent=False):
        result = False
        if not self.is_empty():
            message_result = None
            if not silent:
                message_result = show_message_box(CLEAR_WARNING, 
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

    def delete(self, event=None):
        if show_message_box(LIST_DELETE_WARNING) == OK:
            self.player._stop()
            self.player.eject()
            self.clear(silent=True)
            remove_file(self.save_file_path, self.log)
            remove_dir(self.playback_dir)
            self.save_file_path = self.get_new_list_path()
            self.playback_dir = self.get_playback_dir_path(self.save_file_path)
            if os.path.exists(self.playback_dir):
                remove_dir(self.playback_dir)
            os.mkdir(self.playback_dir)
            self.save(check_filenames=False)
        self.player.setFocus()
    
    def project_is_valid(self, load_file_path):
        valid = False
        with open(load_file_path, 'r') as load_file:
            songs_info = json.load(load_file)
        file_names_list = [song_info.get('file_name') for song_info in songs_info]
        playback_dir = self.get_playback_dir_path(load_file_path)
        if not os.path.exists(playback_dir):
            self.log.debug(f'Playback dir not exist! {playback_dir}')
            message_result = show_message_box(FOLDER_NOT_FOUND_WARNING, 
                                            ok_text='Указать папку',
                                            cancel_text='Отменить загрузку списка')
            if message_result == OK:
                new_playback_dir = QtWidgets.QFileDialog.getExistingDirectory(self,
                                                        'Выбрать папку',
                                                        self.options.save_dir())
                if new_playback_dir:
                    try:
                        os.mkdir(playback_dir)
                    except Exception as e:
                        self.log.error(f'Ошибка создания папки {playback_dir}', exc_info=True)
                        return False
                    copy_ok = True
                    for file_name in self.find_files(file_names_list, new_playback_dir, search_in_list=True):
                        copy_ok = copy_ok and copy_file(os.path.join(new_playback_dir, file_name), 
                                                             os.path.join(playback_dir, file_name),
                                                             self.log)
                    if copy_ok:
                        return self.project_is_valid(load_file_path)
                    else:
                        return False
        else:
            self.log.debug(f'playback dir is valid')
            files_not_found = self.find_files(file_names_list, playback_dir, not_found=True) 
            file_path = ''
            show_choice = True
            while files_not_found:
                file_name = files_not_found[0]
                warning = SONGFILE_NOT_FOUND_WARNING.format(file_name)
                self.log.info(f'files not found: {files_not_found}')
                if show_choice:
                    choice_result = show_message_box(warning, 
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
                        self.log.debug('file_path recieved... {file_path}')
                        try_playback_dir, try_file_name = os.path.split(file_path)
                        warning = WRONG_FILE_NAME_WARNING.format(file_name, try_file_name)
                        if try_file_name != file_name and show_message_box(warning, 
                                                    ok_text='Добавить файл',
                                                    cancel_text='Найти другой файл',
                                                    default_button=CANCEL,
                                                    ) == CANCEL:
                            self.log.debug('wrong file! Try to find another. {try_file_name}')
                            file_path = ''
                            continue 
                        if choice_result == OK_CHECKED:
                            self.log.debug('apply OK to all files:')
                            show_choice = False
                            for try_file_name in self.find_files(files_not_found, try_playback_dir):
                                self.log.debug(f'found file: {try_file_name}')
                                if copy_file(os.path.join(try_playback_dir, try_file_name), 
                                             os.path.join(playback_dir, try_file_name),
                                             self.log):
                                    files_not_found.remove(try_file_name)
                                    self.log.debug(f'file copied to {os.path.join(playback_dir, try_file_name)}')
                            if files_not_found:
                                self.log.debug('some files are not found')
                                choice_result = OK
                                file_path = ''
                        else:
                            if copy_file(file_path, os.path.join(playback_dir, file_name),
                                         self.log):
                                files_not_found.remove(file_name)
                    else:
                        show_choice = True
                elif choice_result == CANCEL or choice_result == CANCEL_CHECKED:
                    self.log.debug(f'deleting song {file_name}')
                    if choice_result == CANCEL_CHECKED:
                        songs_info = self.remove_info_by_filename(files_not_found, songs_info)
                        self.log.debug('all songs removed.')
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
            self.log.info('All files found. VALIDATED!')
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
            self.log.debug(f'searching... {song_info.get("name")}')
            if not song_info.get('file_name') in song_filenames: 
                new_songs_info.append(song_info)
            else:
                self.log.debug('song removed')
        return new_songs_info
                
    def set_row(self, target, playing=False):
        if type(target) != int:
            row = self.list.get_song_index(target)    
        else:
            row = target
        current_row = self.list.currentRow()
        self.log.debug(f'from {current_row} to {row}')
        self.list.setCurrentRow(row) # смена строки вызывает change_row,
        row_changed = current_row != row # если строка поменялась
        if not row_changed:
            self.change_row(row)
        if playing:                  
            self.playing = row
        return row_changed
            
    def change_row(self, row):
        self.selected = row
        self.log.debug(f'Selected song index: {self.selected}')
        #print('Player_state:', self.player.state)
        if self.player.state is STOPED:
            self.playing = row
            song = self.song(self.playing)
            if song:
                self.player.eject()
                self.player.load(song)
                self.normal_mode()
            else:
                self.log.debug('Song widget not detected!')
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
        
    def rename_mode(self, event=None, name=None):
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
        
    def get_playback_dir_filenames(self, playback_dir=''):
        playback_dir = playback_dir or self.playback_dir
        self.log.debug(f'playback_dir: {playback_dir}')
        return [f_name.strip() for f_name in os.listdir(playback_dir
                                    ) if not f_name.startswith('.')]
    
    def improve_filename(self, filename):
        self.log.debug(f'source filename: {filename}')
        improved = False
        if not filename.isascii():
            valid_filename_symbols = []
            for s in filename:
                if s not in VALID_SYMBOL_CODES:
                    s = '#'
                    improved = True
                valid_filename_symbols.append(s)
            if improved:
                result = ''.join(valid_filename_symbols)
                self.log.warning(f'filename has changed to {result}')
                return result

    def get_playback_dir_path(self, list_file_path):
        dirname, filename = os.path.split(list_file_path)
        return os.path.join(dirname, os.path.splitext(filename)[0] + '_music')
              
    def get_id(self):   # TODO Переписать как генератор
        id = self.id_source
        self.id_source += 1
        return id
    
    def is_empty(self):
        return not self.list.count() > 0 or False
            
    def set_current_row(self, row):
        self.list.setCurrentRow(row)
        
    def get_song(self, direction='', state=STOPED):
        song = None
        if state != STOPED:
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


@log_class    
class SongList(QtWidgets.QListWidget):
    log = set_logger('SongList')
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
        self.log.debug("List: DROP!!")
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
            self.log.debug(f'drop indicator position: {self.dropIndicatorPosition()}')
            self.log.debug(f'from index {from_index}')
            self.log.debug(f'drop index {drop_index}')
            self.log.debug(f'playing index = {self.widget.playing}')
            super().dropEvent(event)
            self.widget.change_row(drop_index)
            self.widget.save(check_filenames=False)
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
            if song is selected_song:
                return index
                    
    def get_song_by_index(self, index):
        item = self.item(index)
        if item:
            song = self.itemWidget(item)
            return song
    
    def get_song_info(self, song):
        #waveform = song.waveform or []
        song_info = {'id': song.id,
                    'name': song.name,
                    'file_name': song.file_name,
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

 