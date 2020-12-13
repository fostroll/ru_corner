#-*- encoding: utf-8 -*-

import os

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
