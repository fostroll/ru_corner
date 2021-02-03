#-*- encoding: utf-8 -*-

from bs4 import BeautifulSoup
from html import unescape
from html.parser import HTMLParser
import os
import random
import re
import requests
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)
from subprocess import Popen, PIPE
import sys
import tempfile
import textract
import time


PRJNAME = 'ru_corner'
DATA_DIR_NAME = '_data'
CURR_PATH = os.path.abspath(sys.argv[0])
GET_URL_TIMEOUT = 10  # seconds
GET_URL_RETRY_TIMEOUT = 20  # seconds
GET_URL_RETRY_CONNERROR = 60  # seconds
SOFFICE = r'"C:\Program Files\LibreOffice\program\soffice.com"'
PDFTOTEXT = r'pdftotext.exe'

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
     return unescape(text.replace('&shy;', '')) \
         .replace('\u00a0', ' ') \
         .replace('\u200b', '').replace('\ufeff', '') \
         .replace('й', 'й').replace('ё', 'ё') \
         .replace('΄', '').strip()

def shuffle_file_list(fns, new_order=None, keep_first=0):
     fns = sorted(fns)
     if keep_first:
         fns = fns[prevent_first:]
     if not new_order:
         new_order = list(range(len(fns)))
         random.shuffle(new_order)
     assert len(new_order) == len(fns)
     new_fns = [fns[i] for i in new_order]
     tmp_fns = [x + '$' for x in new_fns]
     for fn, new_fn in zip(fns, tmp_fns):
         os.rename(fn, new_fn)
     for fn, new_fn in zip(tmp_fns, new_fns):
         os.rename(fn, new_fn)
     return new_order

def convert_odt(fn_in, fn_out=None):
#    proc = Popen('{} --nolockcheck --headless --convert-to txt:Text {}'
#                     .format(SOFFICE, fn_in))
    proc = Popen('{} --nolockcheck --cat {}'.format(SOFFICE, fn_in),
                 shell=True, stdout=PIPE)
    text = b''
    for line in proc.stdout:
        text += line
#        sys.stdout.buffer.write(line)
#        sys.stdout.buffer.flush()
    proc.stdout.close()
    proc.wait()
    text = text.decode('cp1251', errors='strict')
    if fn_out:
        with open(fn_out, 'wt', encoding='utf-8') as f:
             f.write(text)
    return text

def convert_doc(fn_in, fn_out=None):
    lang = os.environ.get('LANG')
    for LANG in ['ru_RU.UTF-8', 'ru_RU.CP1251']:
        try:
            os.environ['LANG'] = LANG
            text = textract.process(fn_in, encoding='utf-8')
            text = text.decode('utf-8')
            if fn_out:
                with open(fn_out, 'wt', encoding='utf-8') as f:
                     f.write(text)
            break
        except (textract.exceptions.ShellError,
                UnicodeDecodeError, TypeError) as e:
            pass
    else:
        text = convert_odt(fn_in, fn_out)
    if lang:
        os.environ['LANG'] = lang
    else:
        del os.environ['LANG']
    return text

def convert_pdf(fn_in, fn_out=None):
    #pdftotext -enc UTF-8 [-layout] [-raw] [-simple] [-simple2] -nopgbrk pdf_fn txt_fn
    fn_out_ = fn_out if fn_out else next(tempfile._get_candidate_names())
    try:
        for key in ['simple', 'raw']:
            proc = Popen('{} -enc UTF-8 -{} -nopgbrk {} {}'
                              .format(PDFTOTEXT, key, fn_in, fn_out_),
                         shell=True, stdout=None)
            proc.wait()
            with open(fn_out_, 'rt', encoding='utf-8') as f:
                text = f.read()
            if len([x for x in text.split('\n') if ' ' * 20 in x]) < 20:
                break
    finally:
        if not fn_out:
            os.remove(fn_out_)
    return text

def convert_html(fn_in, fn_out=None):

    class HTMLFilter(HTMLParser):
        text = ''
        def handle_data(self, data):
            self.text += data

    def norm(text):
        text = re.sub(r'\s+', ' ', text).replace('\n', ' ')
        text = re.sub(r'(<(?:(?:[pP]|[dD][dD]|[hH]\d)[ >]|[bB][rR][> /]))',
                      r'\n\g<1>', text)
        text = re.sub(r'(</(?:[pP]|[dD][dD]|[hH]\d|[bB][rR])>)',
                      r'\g<1>\n', text)
        text = re.sub(r'</(?:[bB]|strong|STRONG)>\s*<(?:[bB]|strong|STRONG)>',
                      '', text)
        text = re.sub(r'<(/)?(?:[bB]|strong|STRONG)>', r'[[\g<1>b]]', text)
        return text

    with open(fn_in, 'rt', encoding='utf=8') as f:
        pres = re.split('<[pP][rR][eE][^>]*>', f.read())
        text = norm(pres[0])
        for pre in pres[1:]:
            chunks = re.split('</[pP][rR][eE]>', pre)
            text += '<pre>' + chunks[0] + '</pre>'
            chunks = norm(' '.join(chunks[1:]))
            text += chunks
        f = HTMLFilter()
        f.feed(text)
        text = f.text
        #bs = BeautifulSoup(text, features='lxml')
        #text = bs.get_text()
    text = re.sub(r'(^|\n)\s*\[\[b]](.+?)\[\[/b]]', r'\g<1>\g<2>: ', text)
    text = text.replace('[[b]]', '')
    text = text.replace('[[/b]]', '')
    if fn_out:
        with open(fn_out, 'wt', encoding='utf-8') as f:
             f.write(text)
    return text
