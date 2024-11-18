import inspect
import logging
import os
import sys
from PyQt5 import QtWidgets
from shutil import copyfile, rmtree

LOGGING_LEVEL = logging.INFO
#LOGGING_LEVEL = logging.DEBUG
NO_LOG_CLASSES = ()
NO_LOG_METHODS = ('__str__',
                  'song', 
                  'get_song_by_index',
                  'scale_number',
                  'paintEvent',
                  'update_playback_slider',
                  'min_sec_from_ms',
                  )
INFO_LOG_PATH = 'logs/info.log'
ERROR_LOG_PATH = 'logs/error.log'
if not os.path.exists('logs'):
    os.mkdir('logs')
open(INFO_LOG_PATH, 'w+').close()
open(ERROR_LOG_PATH, 'a+').close()
error_handler = logging.FileHandler(ERROR_LOG_PATH, mode='a')
error_formatter = logging.Formatter("%(asctime)s %(levelname)s [%(filename)s/%(name)s/%(funcName)s/%(lineno)s] %(message)s")
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(error_formatter)
ERROR_HANDLER = error_handler
debug_handler = logging.StreamHandler(stream=sys.stdout)
debug_formatter = logging.Formatter("{levelname}\t{message} [{name}/{funcName}/{lineno}]", style='{')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(debug_formatter)
DEBUG_HANDLER = debug_handler

indent = ''
nested = False
            
VALID_SYMBOL_CODES = (tuple(chr(s) for s in range(1040, 1104)) + 
                        tuple(chr(s) for s in range(128)) + ('ё', 'Ё'))
                        
BASE_DIR = os.path.dirname(__file__)
USER_HOME_DIR = os.path.expanduser('~')
USER_MUSIC_DIR = USER_HOME_DIR

SONG_ITEM_UI_PATH = os.path.join(BASE_DIR, 'GUI/songItem.ui')
SONG_LIST_UI_PATH = os.path.join(BASE_DIR, 'GUI/songList.ui')
MAIN_WINDOW_UI_PATH = os.path.join(BASE_DIR, 'GUI/main_window.ui')
OPTIONS_DIALOG_UI_PATH = os.path.join(BASE_DIR, 'GUI/options.ui')
DEFAULT_SIGNAL_PATH = os.path.join(BASE_DIR, 'assets/signal.wav')

DEFAULT_PLAYBACK_DIR = os.path.join(USER_MUSIC_DIR, 'song_lists/new_songlist_music')
DEFAULT_SAVE_DIR = os.path.join(USER_MUSIC_DIR, 'song_lists')
SONG_LIST_EXTENSION = '.sl'
SUPPORTED_FILE_TYPES = '.mp3', 'mp4', '.wav', '.m4a', '.mpeg'
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
                   'hard_link_filename': False,
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
NEW_LIST_WARNING = 'Создать новый пустой список?\nТекущий список будет закрыт.'
LIST_FILE_EXISTS_WARNING = 'Список с именем {} уже есть!\nВсё его содержимое будет перезаписано!'
SONG_NAME_EXISTS_WARNING = 'Песня с таким именем уже есть в списке!'
CLEAR_WARNING = 'Удалить все песни из списка? \nФайлы песен останутся папке списка.'
DELETE_SONG_WARNING = 'Точно удалить?'
DELETE_PLAYING_WARNING = 'Нельзя удалить то, что сейчас играет!'
SOURCE_DELETE_WARNING = '''Песни {} больше нет в списке, но файл с ней ещё остался.
Удалить файл или оставить в папке списка?'''
LIST_DELETE_WARNING = 'Полностью удалить список и связанные с ним файлы?'
RESET_SONG_SETTINGS_WARNING = 'Настройки громкости и позиции будут сброшены!'
HARD_LINK_ENABLE_WARNING = '''Если в списке есть копии песен с разными именами, при сохранении настроек для каждой из них будет создан отдельный файл\n
Это потребует больше места на диске'''

WAVEFORM_ERROR_WARNING = 'Ошибка при построении формы волны!\nПодробнее в logs/error.log'
SONG_LIST_SAVING_ERROR_WARNING = 'СПИСОК НЕ СОХРАНЁН!\n{}\nподробнее в logs/error.log'
FILE_ACCESS_ERROR = 'ОШИБКА ДОСТУПА К ФАЙЛУ! {filename}\n{error}'
FILE_COPYING_ERROR = 'ФАЙЛ {filename} НЕ СКОПИРОВАН!\n{error}'
LIST_LOADING_ERROR = 'ОШИБКА ЗАГРУЗКИ СПИСКА!\nПодробнее в logs/error.log'


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

def set_logger(class_name):
    logger = logging.getLogger(class_name)
    logger.setLevel(LOGGING_LEVEL)
    logger.addHandler(ERROR_HANDLER)
    logger.addHandler(DEBUG_HANDLER)
    return logger
    
def to_log(func):
    def auto_log(self, *args, **kwargs):
        global indent, nested
        func_name = func.__name__
        nested = False
        indent += '..'
        self.log.info(f'{indent}>>{func_name}'.upper())
        result = func(self, *args, **kwargs)
        str_result = f'{indent}{result}'[:300]
        #print(f'nested: {nested}')
        if nested or result != None:
            if result != None:
                self.log.debug(f'{indent}{func_name} result: {str_result}')
            self.log.info(f'{indent}{func_name}<<'.upper())
        nested = True
        indent = indent[2:]
        return result
    return auto_log

def log_class(logged_class):
    if logged_class.__name__ not in NO_LOG_CLASSES:
        for name, method in inspect.getmembers(logged_class):
            if inspect.isfunction(method):
                if name in NO_LOG_METHODS:
                    continue
                setattr(logged_class, name, to_log(method))
    return logged_class
    
logging.basicConfig(level=logging.INFO, filename=INFO_LOG_PATH,filemode="w",
                    format="%(asctime)s %(levelname)s\t%(message)s [/%(name)s/%(funcName)s:%(filename)s]")
log = set_logger(__name__)

def show_message_box(message, 
                     checkbox_text='', 
                     ok_text='OK', 
                     cancel_text='Отмена',
                     middle_text='',
                     default_button=OK,
                     log=log):
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
    log.debug(f'MESSAGE BOX RESULT: {result}')
    return result

def remove_file(filepath, logger=log):
    result = False
    try:
        os.remove(filepath)
        result = True
    except Exception as e:
        logger.error(f'Ошибка удаления файла!', exc_info=True)
        show_message_box(FILE_ACCESS_ERROR.format(filename=filepath, 
                                                       error=e), 
                              cancel_text=''
                              ) 
    finally:
        return result   

def copy_file(from_dir, to_dir, logger=log, overwrite=False):
    result = False
    filename = os.path.basename(from_dir)
    try:
        copyfile(from_dir, to_dir)
        result = True
    except SameFileError as e:
        if overwrite:
            remove_file(to_dir, logger)
            copyfile(from_dir, to_dir)
            result = True
            logger.info(f'Файл {to_dir} уже существует и был перезаписан')
        else:
            logger.error(f'Файл {filename} из {from_dir} уже существует в {to_dir}', exc_info=True)
            show_message_box(FILE_COPYING_ERROR.format(filename=filename, 
                                                            error=e), 
                                  cancel_text=''
                                  )
    except Exception as e:
        logger.error(f'Ошибка копирования файла {filename} из {from_dir} в {to_dir}', exc_info=True)
        show_message_box(FILE_COPYING_ERROR.format(filename=filename, 
                                                        error=e), 
                              cancel_text=''
                              ) 
    finally:
        return result

def remove_dir(dirpath, logger=log):
    try:
        rmtree(dirpath)
    except Exception as e:
        logger.error('Ошибка удаления папки с файлами!', exc_info=True)
        show_message_box('Ошибка удаления папки с файлами!', cancel_text='')