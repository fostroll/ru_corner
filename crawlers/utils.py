#-*- encoding: utf-8 -*-

from collections import OrderedDict
from corpuscula import Conllu
import glob
import os
import requests
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)
import sys
import time
from toxine.text_preprocessor import TextPreprocessor

from _utils_add import _path, _sub_idx, DATA_DIR_NAME


CURR_PATH = os.path.abspath(sys.argv[0])
CURR_DIR = os.path.dirname(CURR_PATH)
DATA_EXT = '.txt'
GET_URL_TIMEOUT = 10  # seconds
GET_URL_RETRY_TIMEOUT = 20  # seconds
GET_URL_RETRY_CONNERROR = 60  # seconds

#TEMP_DIR = os.path.join(*_path[:_sub_idx], DATA_DIR_NAME, '_tmp')
#if not os.path.isdir(TEMP_DIR):
#    os.makedirs(TEMP_DIR)
def setdir_(suffix):
    dir_ = os.path.join(*_path[:_sub_idx], DATA_DIR_NAME, suffix,
                        *_path[_sub_idx + 1:])[:-3]
    if not os.path.isdir(dir_):
        os.makedirs(dir_)
    return dir_
PAGES_DIR = setdir_('pages')
TEXTS_DIR = setdir_('texts')
CHUNKS_DIR = setdir_('chunks')
CONLL_DIR = setdir_('conll')
LINKS_FN = os.path.join(PAGES_DIR, 'links')
TEXTS_FOR_DOMAIN = 10000
_cnt = len([x for x in glob.glob(os.path.join(CURR_DIR, '*.py'))
              if not os.path.basename(x).startswith('_')])
TEXTS_FOR_SOURCE = TEXTS_FOR_DOMAIN // _cnt \
                 + (TEXTS_FOR_DOMAIN % _cnt != 0)
CHUNKS_FOR_DOMAIN = TEXTS_FOR_DOMAIN
CHUNKS_FOR_SOURCE = CHUNKS_FOR_DOMAIN // _cnt \
                  + (CHUNKS_FOR_DOMAIN % _cnt != 0)
CONLL_FOR_DOMAIN = 1000
CONLL_FOR_SOURCE = CONLL_FOR_DOMAIN // _cnt \
                 + (CONLL_FOR_DOMAIN % _cnt != 0)

def get_data_path(data_dir, max_files, curr_num):
    return os.path.join(data_dir, ('{:0' + str(len(str(max_files))) + 'd}')
                                      .format(curr_num)
                                + DATA_EXT)

def get_file_list(data_dir, max_files):
    return glob.glob(
        os.path.join(data_dir, '?' * len(str(max_files)) + DATA_EXT)
    )

def fn_to_id(fn):
    return os.path.split(fn)[-1].replace(DATA_EXT, '')

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

def norm_text(text):
    text = text.replace('Й', 'Й').replace('й', 'й') \
               .replace('Ё', 'Ё').replace('ё', 'ё')
    if '‛' in text or '‘' in text:
        text = text.replace('‛', '«').replace('‘', '«').replace('’', '»')
    return text

def tokenize(num_links, isdialog=True):
    tp = TextPreprocessor()
    chunk_fns = get_file_list(CHUNKS_DIR, num_links)
    max_conll = min(CONLL_FOR_SOURCE, len(chunk_fns))
    texts_processed = 0
    for chunk_idx, chunk_fn in enumerate(chunk_fns[:CONLL_FOR_SOURCE],
                                         start=1):
        conll_fn = chunk_fn.replace(CHUNKS_DIR, CONLL_DIR)
        assert conll_fn != chunk_fn, 'ERROR: invalid path to chunk file'
        if not os.path.isfile(conll_fn):
            with open(chunk_fn, 'rt', encoding='utf-8') as f_in:
                pars = norm_text(f_in.read()).split('\n')

            if isdialog:
                text = [x.split('\t') for x in pars if x]
                curr_speaker = None

                speakers, pars = [], []
                for speaker, sentence in text:
                    if speaker:
                        if speaker != curr_speaker:
                            curr_speaker = speaker
                    else:
                        speaker = curr_speaker
                    speakers.append(curr_speaker)
                    pars.append(sentence)
                speaker_list = \
                    {x: str(i) for i, x in
                         enumerate(OrderedDict(zip(speakers, speakers)),
                                   start=1)}

            doc_id = fn_to_id(conll_fn)
            tp.new_doc(doc_id=doc_id, metadata=[])
            tp.new_pars(pars, doc_id=doc_id)
            tp.do_all(tag_email=False, tag_phone=False, tag_date=False,
                      silent=True)
            conll = list(tp.save(doc_id=doc_id))
            tp.remove_doc(doc_id)

            if isdialog:
                speakers = iter(speakers)
                for sentence in conll:
                    sent, meta = sentence
                    if not any(x.isalnum() for x in meta['text']):
                        continue
                    if 'newpar id' in meta:
                        meta['speaker'] = speaker_list[next(speakers)]

            Conllu.save(conll, conll_fn, log_file=None)
            print('\r{} (of {})'.format(chunk_idx, max_conll),
                  end='')
            texts_processed += 1
    if texts_processed:
        print()
