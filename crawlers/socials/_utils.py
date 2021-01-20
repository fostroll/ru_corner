#-*- encoding: utf-8 -*-

import os
import re
from selenium.common.exceptions import TimeoutException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import shutil
import time

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
SEARCH_DEPTH = 2
POST_LIMIT = 20

def parse_credentials(creds_fn):
    def parse(token):
        token = token.strip()
        if token[0] in '\'"' and token[-1] in '\'"':
            token = token[1:-1].strip()
        assert token, 'ERROR: line "{}" in credentials file is ' \
                      'not a valid credential'.format(line)
        return token

    with open(creds_fn) as f:
        for line in f:
            line = line.strip()
            if not line.startswith('#'):
                creds = line.split('=', maxsplit=1)
                assert len(creds) == 2, \
                    'ERROR: line "{}" in credentials file is ' \
                    'not a valid credential'.format(line)
                yield parse(creds[0]).lower(), parse(creds[1])

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

#def make_chunks():
#    for fn in os.listdir(utils.TEXTS_DIR):
#        src = os.path.join(utils.TEXTS_DIR, fn)
#        dst = os.path.join(utils.CHUNKS_DIR, fn)
#        if os.path.isdir(src):
#            raise ValueError()
#            shutil.copytree(s, d, symlinks, ignore)
#        else:
#            shutil.copy2(src, dst)

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
                f_in.readline()
                text = f_in.read()
                text = re.sub(r'[\u2800\uFE00-\uFE0F]', '', text)
                lines = ('\t'.join(x.strip() for x in x.split('\t'))
                             for x in text.split('\n')
                             if re.search('\w', x)
                            and not all(x.startswith('#') for x in x.split()))
                #lines = (x.strip() for x in text.split('\n')
                #                   if re.search('\w', x)
                #                  and not all(x.startswith('#')
                #                                  for x in x.split()))
                f_out.write('\n'.join(x for x in lines if x))
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

def selenium_scroll_to_bottom(driver, sleep=5):
    page_len = driver.execute_script(
        'window.scrollTo(0, document.body.scrollHeight);'
        'var lenOfPage=document.body.scrollHeight;'
        'return lenOfPage;'
    )
    time.sleep(sleep)  # TODO: replace to some load detection method
    return page_len

def selenium_scroll_to_top(driver, sleep=0):
    page_len = driver.execute_script(
        'window.scrollTo(0, 0);'
    )
    time.sleep(sleep)

def selenium_scroll_into_view(driver, elem, sleep=1):
    driver.execute_script(
        'arguments[0].scrollIntoView(true);', elem
    )
    time.sleep(sleep)

def selenium_scroll_by(driver, x, y, sleep=1):
    driver.execute_script('window.scrollBy({}, {});'.format(x, y))
    time.sleep(sleep)

def selenium_open_new_window(driver, url):
    driver.execute_script('window.open("{}");'.format(url))
    driver.switch_to.window(driver.window_handles[-1])

def selenium_close_window(driver):
    if len(driver.window_handles) > 1:
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
    else:
        driver.quit()

def selenium_click(driver, elem=None, stale_elem=None, visible_elem=None,
                   max_tries=None, timeout_warning=None):
    try_ = 1
    while True:
        try:
            if elem:
                elem.click()
            if stale_elem or not visible_elem:
                WebDriverWait(driver, 10) \
                    .until(EC.staleness_of(stale_elem or elem))
            if visible_elem:
                WebDriverWait(driver, 10) \
                    .until(EC.visibility_of_element_located(visible_elem))
            break
        except TimeoutException as e:
            if max_tries and try_ >= max_tries:
                raise e
            if timeout_warning:
                print(timeout_warning)
            try_ += 1

def selenium_ctrl_click(driver, elem, sleep=5):
    ActionChains(driver).key_down(Keys.CONTROL).click(elem) \
                        .key_up(Keys.CONTROL).perform()
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(sleep)

def selenium_move_to_element(driver, elem, x=None, y=None, sleep=0):
    action = webdriver.ActionChains(driver)
    if x is None or y is None:
        action.move_to_element(elem)
    else:
        action.move_to_element_with_offset(elem, x, y)
    action.perform()
    time.sleep(sleep)

def selenium_remove(driver, elem):
    driver.execute_script(
       'var element = arguments[0]; element.parentNode.removeChild(element);',
       elem
    )
