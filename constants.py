import logging
import os
import sys

LOGGING_LEVEL = logging.INFO
#LOGGING_LEVEL = logging.DEBUG

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
debug_formatter = logging.Formatter("{levelname}\t[{name}/{funcName}/{lineno}]: {message}", style='{')
debug_handler.setLevel(logging.DEBUG)
debug_handler.setFormatter(debug_formatter)
DEBUG_HANDLER = debug_handler

def set_log(class_name):
    logger = logging.getLogger(class_name)
    logger.setLevel(LOGGING_LEVEL)
    logger.addHandler(ERROR_HANDLER)
    logger.addHandler(DEBUG_HANDLER)
    return logger

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
DELETE_SONG_WARNING = 'Точно удалить?'
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