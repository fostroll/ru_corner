#-*- encoding: utf-8 -*-

import os
import shutil

###
import sys
sys.path.append('../')
###
import utils


MIN_TEXT_LINES = 1
MIN_CHUNK_LINES = 1
MIN_CHUNK_WORDS = 20
MAX_CHUNK_WORDS = 200
PAGE_LINKS_FN = os.path.join(utils.PAGES_DIR, 'page_links')
NUM_AUTHORS = 10
SEARCH_DEPTH = 2
POST_LIMIT = 20

def load_page_links():
    start_link_idx, page_links = 0, []
    fn = PAGE_LINKS_FN
    if os.path.isfile(fn):
        with open(PAGE_LINKS_FN, 'rt', encoding='utf-8') as f:
            lines = [x for x in f.read().split('\n') if x]
            if lines:
                start_link_idx = None
                page_links = [x.split('\t') for x in lines if x]
    if start_link_idx == 0:
        fn += '.tmp'
        if os.path.isfile(fn):
            with open(fn, 'rt', encoding='utf-8') as f:
                lines = [x for x in f.read().split('\n') if x]
                if lines:
                    start_link_idx = int(lines[0])
                    page_links = [x.split('\t') for x in lines[1:] if x]
    return start_link_idx, page_links

def save_page_links(start_link_idx, page_links):
    fn = PAGE_LINKS_FN
    lines = ['\t'.join(x) for x in page_links]
    if start_link_idx is not None:
        fn += '.tmp'
        lines = [str(start_link_idx)] + lines
    with open(fn, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def make_chunks():
    for fn in os.listdir(utils.TEXTS_DIR):
        src = os.path.join(utils.TEXTS_DIR, fn)
        dst = os.path.join(utils.CHUNKS_DIR, fn)
        if os.path.isdir(src):
            raise ValueError()
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(src, dst)

def make_chunks(num_links, min_chunk_lines=MIN_CHUNK_LINES):
    text_fns = utils.get_file_list(utils.TEXTS_DIR, num_links)
    max_chunks = min(utils.CHUNKS_FOR_SOURCE, len(text_fns))
    texts_processed = 0
    for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                       start=1):
        chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
        assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
        if not os.path.isfile(chunk_fn):
            with open(text_fn, 'rt', encoding='utf-8') as f_in, \
                 open(chunk_fn, 'wt', encoding='utf-8') as f_out:
                lines = f_in.read().split('\n')[1:]
                f_out.write('\n'.join(lines))
                print('\r{} (of {})'.format(text_idx, max_chunks),
                      end='')
                texts_processed += 1
    if texts_processed:
        print()
