#-*- encoding: utf-8 -*-

from collections import OrderedDict
from corpuscula import Conllu
import glob
import os
import re
import sys
import time
from toxine.text_preprocessor import TextPreprocessor

from _utils_add import get_url, _path, _sub_idx, DATA_DIR_NAME


CURR_PATH = os.path.abspath(sys.argv[0])
CURR_DIR = os.path.dirname(CURR_PATH)
DATA_EXT = '.txt'

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

def norm_text(text):
    text = text.replace('*', ' ').replace('•', ' ').replace('⁄', '/') \
               .replace('Й', 'Й').replace('й', 'й') \
               .replace('Ё', 'Ё').replace('ё', 'ё') \
               .replace('<..>', ' ').replace('<...>', ' ') \
               .replace('❝', '«').replace('❞', '»')
    text = re.sub('([А-Яа-я])ó', r'\g<1>о', text)
    text = re.sub('ó([а-я])', r'о\g<1>', text)
    text = re.sub('['
        '\ufff0-\uffff'
        '\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF'
        '\U00020000-\U0002A6DF\U0002A700-\U0002CEAF\U0002F800-\U0002FA1F'
    ']', ' ', text)

    if '‛' in text or '‘' in text:
        text = text.replace('‛', '«').replace('‘', '«').replace('’', '»')
    else:
        text = text.replace('’', "'")
    text = text.strip()

    if any(x in 'ЀЂЃЄЅІЇЈЉЊЋЌЍЎЏѐђѓєѕіїјљњћќѝўџѠѡѢѣѤѥѦѧѨѩѪѫѬѭѮѯѰѱѲѳѴѵѶѷѸѹѺѻѼѽ'
                'ѾѿҀҁ҂҃҄҅҆҇҈҉ҊҋҌҍҎҏҐґҒғҔҕҖҗҘҙҚқҜҝҞҟҠҡҢңҤҥҦҧҨҩҪҫҬҭҮүҰұҲҳҴҵҶҷҸҹ'
                'ҺһҼҽҾҿӀӁӂӃӄӅӆӇӈӉӊӋӌӍӎӏӐӑӒӓӔӕӖӗӘәӚӛӜӝӞӟӠӡӢӣӤӥӦӧӨөӪӫӬӭӮӯӰӱӲӳӴӵ'
                'ӶӷӸӹӺӻӼӽӾӿ' for x in text):
       text = None
#    a = ''.join(sorted(set(x for x in text if x > 'ё' and ord(x) <= 0x4ff)))
#        '–—―−“”„…'
#      + '₠₡₢₣₤₥₦₧₨₩₪₫€₭₮₯₰₱₲₳₴₵₶₷₸₹₺₻₼₽₾₿'
#      + '№'
#      + '\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200A\u202F\u205F\u2060\u3000'
#      + ''.join(chr(x) for x in range(0x2600, 0x26ff)))))
#    if a:
#        print('[' + a + ']')

    return text

def tokenize(num_links, isdialog=True):
    tp = TextPreprocessor()
    chunk_fns = get_file_list(CHUNKS_DIR, num_links)
    max_conll = min(CONLL_FOR_SOURCE, len(chunk_fns))
    chunk_no, texts_processed = 1, 0
    for chunk_fn in chunk_fns:
        conll_fn = chunk_fn.replace(CHUNKS_DIR, CONLL_DIR)
        assert conll_fn != chunk_fn, 'ERROR: invalid path to chunk file'
        if not os.path.isfile(conll_fn):
            with open(chunk_fn, 'rt', encoding='utf-8') as f_in:
                text = norm_text(f_in.read())
                if not text:
                    continue
                pars = text.split('\n')

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
            tp.do_all(tag_phone=False, tag_date=False, silent=True)
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
            print('\r{} (of {})'.format(chunk_no, max_conll),
                  end='')
            texts_processed += 1
        chunk_no += 1
        if chunk_no > max_conll:
            break
    if texts_processed:
        print()
