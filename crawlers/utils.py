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


PRJNAME = 'ru_corner'
CURR_PATH = os.path.abspath(sys.argv[0])
CURR_DIR = os.path.dirname(CURR_PATH)
DATA_EXT = '.txt'
MIN_TEXT_LINES = 12
MIN_CHUNK_LINES = 6
MIN_CHUNK_WORDS = 200
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
_data_dir_name = 'data'
#TEMP_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, '_tmp')
TEXTS_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'texts',
                          *_path[_sub_idx + 1:])[:-3]
CHUNKS_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'chunks',
                          *_path[_sub_idx + 1:])[:-3]
CONLL_DIR = os.path.join(*_path[:_sub_idx], _data_dir_name, 'conll',
                         *_path[_sub_idx + 1:])[:-3]
LINKS_FN = os.path.join(TEXTS_DIR, 'links')
TEXTS_FOR_DOMAIN = 10000
_cnt = len(glob.glob(os.path.join(CURR_DIR, '*.py')))
TEXTS_FOR_SOURCE = TEXTS_FOR_DOMAIN // _cnt \
                 + (TEXTS_FOR_DOMAIN % _cnt != 0)
CHUNKS_FOR_DOMAIN = TEXTS_FOR_DOMAIN
CHUNKS_FOR_SOURCE = CHUNKS_FOR_DOMAIN // _cnt \
                  + (CHUNKS_FOR_DOMAIN % _cnt != 0)
CONLL_FOR_DOMAIN = 1000
CONLL_FOR_SOURCE = CONLL_FOR_DOMAIN // _cnt \
                 + (CONLL_FOR_DOMAIN % _cnt != 0)

#if not os.path.isdir(TEMP_DIR):
#    os.makedirs(TEMP_DIR)
if not os.path.isdir(TEXTS_DIR):
    os.makedirs(TEXTS_DIR)
if not os.path.isdir(CHUNKS_DIR):
    os.makedirs(CHUNKS_DIR)
if not os.path.isdir(CONLL_DIR):
    os.makedirs(CONLL_DIR)

def get_data_path(data_dir, max_files, curr_num):
    return os.path.join(data_dir,
                        ('{:0' + str(len(str(max_files))) + 'd}')
                            .format(curr_num)
                      + DATA_EXT)

def get_file_list(data_dir, max_files):
    return glob.glob(
        os.path.join(data_dir,
                     '?' * len(str(max_files)) + DATA_EXT)
    )

def fn_to_id(fn):
    return os.path.split(fn)[-1].replace(DATA_EXT, '')

def get_url(url):
    errors = 0
    while True:
        try:
            res = requests.get(url, allow_redirects=True,
                               timeout=GET_URL_TIMEOUT, verify=False)
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

def make_chunks(num_links, moderator=None):
    text_fns = get_file_list(TEXTS_DIR, num_links)
    texts_processed = 0
    for text_idx, text_fn in enumerate(text_fns[:CHUNKS_FOR_SOURCE],
                                       start=1):
        chunk_fn = text_fn.replace(TEXTS_DIR, CHUNKS_DIR)
        assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
        if not os.path.isfile(chunk_fn):
            with open(text_fn, 'rt', encoding='utf-8') as f_in:
                text = \
                    [x.split('\t') for x in f_in.read().split('\n') if x][1:]
            with open(chunk_fn, 'wt', encoding='utf-8') as f_out:
                moder_ = None
                for start_idx, (speaker, _) in enumerate(text):
                    if speaker and (not moderator or speaker == moderator):
                        moder_ = speaker
                        break
                if moderator:
                    moder = moderator
                else:
                    assert moder_, 'ERROR: invalid file content'
                    speaker_lines, speaker_words = {}, {}
                    curr_speaker = None
                    for speaker, line in text:
                        if speaker:
                            curr_speaker = speaker
                            speaker_lines[speaker] = \
                                speaker_lines.get(speaker, 0) + 1
                        if curr_speaker:
                            speaker_words[curr_speaker] = \
                                speaker_words.get(curr_speaker, 0)\
                              + len(line.split())
                    max_lines = max(speaker_lines.values())
                    moder = \
                        min({x: y / speaker_lines[x]
                                 for x, y in speaker_words.items()
                                 if speaker_lines[x] > max_lines / 2}.items(),
                            key=lambda x: x[1])[0]
                eff_start_idx = len(text) * 2 // 3
                for i, (speaker, _) in \
                        enumerate(reversed(text[:eff_start_idx + 1])):
                    if speaker == moder:
                        eff_start_idx -= i
                        break
                else:
                    for i, (speaker, _) in enumerate(text[eff_start_idx:]):
                        if speaker == moder:
                            eff_start_idx += i
                            break
                    else:
                        eff_start_idx = start_idx

                end_idx, next_id = 0, 0
                for idx, (speaker, _) in reversed(list(enumerate(text))):
                    if speaker:
                        if not end_idx:
                            end_idx = idx + 1
                        if speaker == moder:
                            end_idx = idx
                            break
                        if next_id > 2:
                            break
                        next_id += 1

                text = text[start_idx:end_idx]
                lines = []
                speaker_no, chunk_words = 0, 0
                for speaker, line in text[eff_start_idx:]:
                    if speaker:
                        speaker_no += 1
                        if chunk_words >= MIN_CHUNK_WORDS \
                       and speaker_no > MIN_CHUNK_LINES:
                            break
                    lines.append('\t'.join([speaker, line]))
                    chunk_words += len(line.split())
                else:
                    for speaker, line in reversed(text[:eff_start_idx]):
                        lines.insert(0, '\t'.join([speaker, line]))
                        chunk_words += len(line.split())
                        if speaker:
                            speaker_no += 1
                        if chunk_words >= MIN_CHUNK_WORDS 
                       and ((speaker == moder
                         and speaker_no >= MIN_CHUNK_LINES)
                         or speaker_no >= MIN_CHUNK_LINES + 2):
                            break
                f_out.write('\n'.join(lines))
                print('\r{} (of {})'.format(text_idx, CHUNKS_FOR_SOURCE),
                      end='')
                texts_processed += 1
    if texts_processed:
        print()

def tokenize(num_links):
    tp = TextPreprocessor()
    chunk_fns = get_file_list(CHUNKS_DIR, num_links)
    texts_processed = 0
    for chunk_idx, chunk_fn in enumerate(chunk_fns[:CONLL_FOR_SOURCE],
                                         start=1):
        conll_fn = chunk_fn.replace(CHUNKS_DIR, CONLL_DIR)
        assert conll_fn != chunk_fn, 'ERROR: invalid path to chunk file'
        if not os.path.isfile(conll_fn):
            doc_id = fn_to_id(conll_fn)
            with open(chunk_fn, 'rt', encoding='utf-8') as f_in:
                text = [x.split('\t') for x in f_in.read().split('\n') if x]
            tp.new_doc(doc_id=doc_id, metadata=[])
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
                     enumerate(OrderedDict(zip(speakers, speakers)), start=1)}

            tp.new_pars(pars, doc_id=doc_id)
            tp.do_all(silent=True)
            conll = list(tp.save(doc_id=doc_id))
            tp.remove_doc(doc_id)

            speakers = iter(speakers)
            for sentence in conll:
                sent, meta = sentence
                if not any(x.isalnum() for x in meta['text']):
                    continue
                if 'newpar id' in meta:
                    meta['speaker'] = speaker_list[next(speakers)]
            Conllu.save(conll, conll_fn, log_file=None)
            print('\r{} (of {})'.format(chunk_idx, CONLL_FOR_SOURCE),
                  end='')
            texts_processed += 1
    if texts_processed:
        print()
