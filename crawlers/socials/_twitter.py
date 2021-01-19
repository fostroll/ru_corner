#-*- encoding: utf-8 -*-

from collections import OrderedDict
import json
import os
import re
from selenium import webdriver
from selenium.common.exceptions \
    import ElementClickInterceptedException, NoSuchElementException, \
           StaleElementReferenceException
import time

import _utils


LOGIN_URL = 'https://twitter.com'
ROOT_URL = 'https://twitter.com'
CREDENTIALS_FN = '_twitter.credentials.txt'
CREDENTIALS = ['email', 'password']
#COOKIES_FN = '_twitter.cookies.txt'
LOAD_TIMEOUT = 3

creds = dict(_utils.parse_credentials(CREDENTIALS_FN))
assert len(creds) == 2, 'ERROR: invalid credentials file ' + CREDENTIALS_FN
LOGIN, PASSWORD = [creds.get(x) for x in CREDENTIALS]
del creds

def login(driver, login, password, cookies=None):
#    if not cookies and os.path.isfile(COOKIES_FN):
#        with open(COOKIES_FN, 'rt', encoding='utf-8') as f:
#            cookies = json.loads(f.read())
    driver.get(LOGIN_URL)
    if cookies:
        for cookie in cookies:
            driver.add_cookie(cookie)
    if not cookies:
        driver.get(LOGIN_URL + '/login')
        time.sleep(1)
        driver.find_element_by_name('session[username_or_email]') \
              .send_keys(login)
        driver.find_element_by_name('session[password]').send_keys(password)
        elem = driver.find_element_by_css_selector(
            'div[data-testid="LoginForm_Login_Button"]'
        )
        _utils.selenium_click(driver, elem=elem,
            timeout_warning='WARNING: Login timeout. Retrying...'
        )
#        with open(COOKIES_FN, 'wt', encoding='utf-8') as f:
#            f.write(json.dumps(driver.get_cookies()))

def init(cookies=None, silent=False):
    driver = _utils.selenium_init(silent=silent)
    #login(driver, LOGIN, PASSWORD, cookies)
    return driver

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re4 = re.compile(r'#\b\S+\b')
re5 = re.compile(r'\W')
def get_post_text(page_url,
                  min_words=_utils.MIN_CHUNK_WORDS,
                  max_words=_utils.MAX_CHUNK_WORDS,
                  post_limit=_utils.POST_LIMIT,
                  driver=None, cookies=None, silent=False):
    need_quit = False
    if not silent:
        print('START', page_url)
    if not driver:
        need_quit = True
        driver = init(cookies)
    driver.get(page_url)
    time.sleep(LOAD_TIMEOUT)
    page, text = None, None

    class PageEndException(Exception):
        pass

    class PostLimitException(Exception):
        pass

    class PostFoundException(Exception):
        pass

    try:
        labels = set()
        posts, prev_page_len = None, -1
        tries, prev_num_labels = 0, 0
        while True:
            try:
                posts = driver.find_elements_by_css_selector(
                    #'article[role="article"]'
                    'div[data-testid="tweet"]'
                )
                if not silent:
                    print(len(posts))
                post_no, post = 0, None
                for post_no, post in enumerate(posts):
                    try:
                        post = post.find_element_by_xpath(
                            './div/div/div/div[@class="css-901oao r-18jsvk2 r-1qd0xha r-a023e6 r-16dba41 r-ad9z0x r-bcqeeo r-bnwqim r-qvutc0"]'
                        )
                    except NoSuchElementException:
                        continue
                    label = post.text
                    if label not in labels:
                        if not silent:
                            print('post #{} has found'.format(len(labels)))
                        elems = post.find_elements_by_xpath('./*')
                        #text = ' '.join(x.text for x in elems if x.text).strip()
                        text = ''
                        for elem in elems:
                            if elem.tag_name != 'span':
                                text = ''
                                break
                            text += elem.text + ' '
                        #text = unescape(text).replace('\u200b', '') \
                        #                     .replace('\ufeff', '') \
                        #                     .replace('й', 'й') \
                        #                     .replace('ё', 'ё') \
                        #                     .strip()
                        text = utils.norm_text2(text)
                        if not silent:
                            print(text)
                        text0 = re0.sub('', text)
                        text1 = re1.sub('', text0)
                        if text0 and len(text1) / len(text0) >= .9:
                            num_words = len([x for x in re4.sub('', text)
                                                           .split()
                                               if re5.sub('', x)])
                            if not silent:
                                print('<russian>')
                                print(num_words)
                            if num_words >= min_words \
                           and num_words <= max_words:
                                page = post.get_attribute('innerHTML')
                                raise PostFoundException()
                        elif not silent:
                            print('<foreign>')
                        labels.add(label)
                        if len(labels) >= post_limit:
                            text = None
                            raise PostLimitException()
                        text, tries = None, 0
                else:
                    if post:
                        _utils.selenium_scroll_into_view(driver, post)
                    if len(labels) > prev_num_labels:
                        prev_num_labels = len(labels)
                        continue
                    if not silent:
                        print('post #{} is not found'.format(len(labels)))
                    page_len = \
                        _utils.selenium_scroll_to_bottom(driver,
                                                         sleep=LOAD_TIMEOUT)
                    if not silent:
                        print('page_len =', page_len)
                    if page_len == prev_page_len:
                        if tries >= 2:
                            raise PageEndException()
                        tries += 1
                    else:
                        tries = 0
                    prev_page_len = page_len
            except StaleElementReferenceException:
                _utils.selenium_scroll_to_bottom(driver,
                                                 sleep=LOAD_TIMEOUT)
                posts = None

    except (PageEndException, PostLimitException, PostFoundException):
        pass

    if need_quit:
        driver.quit()
    return text, page

def get_trend_authors(trend, num_authors=10, skip_first=0,
                      authors_ignore=None, driver=None, cookies=None,
                      silent=False):
    page_url = ROOT_URL + '/search?q=' + trend + '&src=typed_query'
    need_quit = False
    if not silent:
        print('START', page_url)
    if not driver:
        need_quit = True
        driver = init(cookies)
    driver.get(page_url)
    time.sleep(LOAD_TIMEOUT)
    authors = OrderedDict()
    if authors_ignore is None:
        authors_ignore = OrderedDict()

    class PageEndException(Exception):
        pass

    class AuthorsEnoughException(Exception):
        pass

    try:
        post, prev_page_len = None, -1
        while True:
            tries, errs = 0, 0
            while True:
                try:
                    time.sleep(1)
                    posts = driver.find_elements_by_css_selector(
                        'article[role="article"]'
                    )
                    if not silent:
                        print('found {} posts'.format(len(posts)))
                    #post = None
                    if not posts:
                        try:
                            # it can continue many times. don't worry, just wait
                            btn = driver.find_element_by_xpath(
                                '//div[@class="css-18t94o4 css-1dbjc4n r-urgr8i r-42olwf r-sdzlij r-1phboty r-rs99b7 r-1w2pmg r-1vuscfd r-1dhvaqw r-1ny4l3l r-1fneopy r-o7ynqc r-6416eg r-lrvibr"'
                                  ' or @class="css-18t94o4 css-1dbjc4n r-1q3imqu r-42olwf r-sdzlij r-1phboty r-rs99b7 r-1w2pmg r-1vuscfd r-1dhvaqw r-1ny4l3l r-1fneopy r-o7ynqc r-6416eg r-lrvibr"]'
                            )
                            #print(btn.get_attribute('class'))
                            #print('Twitter raise an error. '
                            #      'Pushing the button...')
                            _utils.selenium_click(driver, elem=btn, max_tries=3)  # exit with error if timeout
                            time.sleep(10)
                            driver.refresh()
                            time.sleep(LOAD_TIMEOUT)
                            errs = 0
                            continue
                        except NoSuchElementException:
                            try:
                                driver.find_element_by_xpath(
                                    '//div[@class="css-901oao r-18jsvk2 r-1qd0xha r-1b6yd1w r-b88u0q r-ad9z0x r-15d164r r-bcqeeo r-q4m81j r-qvutc0"]'
                                )
                                raise PageEndException()
                            except NoSuchElementException:
                                if errs >= 2:
                                    print('Unknown situation, exiting. '
                                          'Manage it manually')
                                    exit()
                                time.sleep(10)
                                errs += 1
                    for post in enumerate(posts):
                        try:
                            post = post.find_element_by_css_selector(
                                'a[class="css-4rbku5 css-18t94o4 css-1dbjc4n r-1loqt21 r-1wbh5a2 r-dnmrzs r-1ny4l3l"]'
                            )
                            href = post.get_attribute('href')
                            text = post.get_attribute('text')
                            if len(authors) < skip_first \
                            or href not in authors_ignore:
                                authors[href] = text
                                authors_ignore[href] = 1
                            if not silent:
                                print(text, href)
                            if len(authors) >= skip_first + num_authors:
                                raise AuthorsEnoughException
                        except NoSuchElementException:
                            continue
                    page_len = \
                        _utils.selenium_scroll_to_bottom(driver,
                                                         sleep=LOAD_TIMEOUT)
                    if not silent:
                        print('page_len =', page_len)
                    if page_len == prev_page_len:
                        if tries >= 2:
                            raise PageEndException()
                        tries += 1
                    else:
                        tries = 0
                    prev_page_len = page_len
                    continue
                    #if post:
                    #    _utils.selenium_scroll_into_view(driver, post_)
                except StaleElementReferenceException:
                    _utils.selenium_scroll_to_bottom(driver,
                                                     sleep=LOAD_TIMEOUT)

    except (PageEndException, AuthorsEnoughException):
        pass

    authors = list(authors.items())[skip_first:skip_first + num_authors]
    if not silent:
        print(authors)
        print(len(authors))
    if need_quit:
        driver.quit()
    return authors
