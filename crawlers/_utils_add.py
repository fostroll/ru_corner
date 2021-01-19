#-*- encoding: utf-8 -*-

from html import unescape
import os
import requests
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)
import sys
import time


PRJNAME = 'ru_corner'
DATA_DIR_NAME = '_data'
CURR_PATH = os.path.abspath(sys.argv[0])
GET_URL_TIMEOUT = 10  # seconds
GET_URL_RETRY_TIMEOUT = 20  # seconds
GET_URL_RETRY_CONNERROR = 60  # seconds

def splitall(path):
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts

_path = splitall(CURR_PATH)
_sub_idx = None
for idx, dir_ in reversed(list(enumerate(_path))):
    if dir_.lower() == PRJNAME.lower():
        _sub_idx = idx + 1
        break
else:
    raise ValueError('ERROR: invalid path')

def get_url(url, headers=None, cookies=None, encoding=None):
    errors = 0
    while True:
        try:
            res = requests.get(url, headers=headers, cookies=cookies,
                               allow_redirects=True, timeout=GET_URL_TIMEOUT,
                               verify=False)
            if encoding:
                res.encoding = encoding
            break
        except requests.exceptions.Timeout:
            print('{}Connect timeout #{}. Waiting...'
                      .format('' if errors else '\n', errors),
                  end='', file=sys.stderr)
            time.sleep(GET_URL_RETRY_TIMEOUT)
            print('\rConnect timeout #{}. Retrying...'.format(errors),
                  file=sys.stderr)
        except requests.exceptions.ConnectionError:
            print('{}Connection error #{}. Waiting...'
                      .format('' if errors else '\n', errors),
                  end='', file=sys.stderr)
            time.sleep(GET_URL_RETRY_CONNERROR)
            print('\rConnection error #{}. Retrying...'.format(errors),
                  file=sys.stderr)
        errors += 1
    return res

def norm_text2(text):
     return unescape(text).replace('\u00a0', ' ') \
                          .replace('\u200b', '').replace('\ufeff', '') \
                          .replace('й', 'й').replace('ё', 'ё') \
                          .strip()
