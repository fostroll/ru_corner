#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

###
import sys
sys.path.append('../')
###
import utils


MIN_TEXT_LINES = 1
MIN_CHUNK_LINES = 1
MIN_CHUNK_WORDS = 20
MAX_CHUNK_WORDS = 250
AUTHORS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'authors_ignore.tmp')
HEADERS = {
    'Host': 'www.avito.ru',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Pragma': 'no-cache',
    'Cache-Control': 'max-age=0',
    'TE': 'Trailers'
}

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

def selenium_init(silent=False):
    options = Options()
    options.add_argument('--disable-infobars')
    options.add_argument('start-maximized')
    options.add_argument('--disable-extensions')
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 1,
        # disable images
        "profile.default_content_settings": {"images": 2},
        "profile.managed_default_content_settings": {"images": 2}
        ###
    })
    options.headless = silent
    driver = webdriver.Chrome(executable_path='chromedriver', options=options)
    driver.maximize_window()
    return driver
