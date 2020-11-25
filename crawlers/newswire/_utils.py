#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os

###
import sys
sys.path.append('../')
###
import utils


MIN_TEXT_LINES = 1
MIN_CHUNK_LINES = 1
MAX_CHUNK_WORDS = 200

def make_chunks(num_links, min_chunk_lines=MIN_CHUNK_LINES):
    text_fns = utils.get_file_list(utils.TEXTS_DIR, num_links)
    max_chunks = min(utils.CHUNKS_FOR_SOURCE, len(text_fns))
    texts_processed = 0
    for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                       start=1):
        chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
        assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
        if not os.path.isfile(chunk_fn):
            with open(text_fn, 'rt', encoding='utf-8') as f_in:
                text = f_in.read().split('\n')[1:]
            with open(chunk_fn, 'wt', encoding='utf-8') as f_out:
                lines, chunk_words = [], 0
                for line_no, line in enumerate(text):
                    if line_no > 0:
                        chunk_words += len(line.split())
                    if line_no < min_chunk_lines \
                    or chunk_words <= MAX_CHUNK_WORDS:
                        lines.append(line)
                    else:
                        break
                f_out.write('\n'.join(lines))
                print('\r{} (of {})'.format(text_idx, max_chunks),
                      end='')
                texts_processed += 1
    if texts_processed:
        print()
