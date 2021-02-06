#-*- encoding: utf-8 -*-

from collections import OrderedDict
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions \
    import ElementClickInterceptedException, NoSuchElementException, \
           StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time

###
import sys
sys.path.append('../')
###
import _utils_add
import _utils


LOGIN_URL = 'https://facebook.com'
ROOT_URL = 'https://www.facebook.com'
CREDENTIALS_FN = '_facebook.credentials.txt'
CREDENTIALS = ['email', 'password']

creds = dict(_utils.parse_credentials(CREDENTIALS_FN))
assert len(creds) == 2, 'ERROR: invalid credentials file ' + CREDENTIALS_FN
LOGIN, PASSWORD = [creds.get(x) for x in CREDENTIALS]
del creds

def login(driver, login, password, cookies=None):
    driver.get(LOGIN_URL)
    if cookies:
        for cookie in cookies:
            driver.add_cookie(cookie)
    else:
        driver.find_element_by_name('email').send_keys(login)
        driver.find_element_by_name('pass').send_keys(password)
        driver.find_element_by_name('login').click()
        while True:
            try:
                WebDriverWait(driver, 10) \
                    .until(EC.presence_of_element_located((By.ID,
                                                           'mount_0_0')))
                break
            except TimeoutException:
                print('WARNING: Login timeout. Retrying...')

def init(cookies=None, silent=False):
    driver = _utils.selenium_init(silent=silent)
    login(driver, LOGIN, PASSWORD, cookies)
    return driver

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re2 = re.compile(r'\s+')
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
    page, text = None, None

    class PageEndException(Exception):
        pass

    try:
        labels = set()
        post, prev_page_len = None, -1
        prev_post = None
        for post_no in range(1, post_limit + 1):
            tries = 0
            while True:
                if not silent:
                    print('post #{}...'.format(post_no))
                post = None
                posts = driver.find_elements_by_css_selector(
                    'div[aria-labelledby]'
                )
                if not silent:
                    print(len(posts))
                for post_ in posts:
                    label = post_.get_attribute('aria-labelledby')
                    #print(label, labels)
                    if label not in labels:
                        labels.add(label)
                        try:
                            # if repost, continue
                            elem = \
                                post_.find_element_by_class_name('hqeojc4l')
                            continue
                        except NoSuchElementException:
                            pass
                        post = prev_post = post_
                        tries = 0
                        break
                else:
                    if not silent:
                        print('post #{} is not found'.format(post_no))
                    page_len = _utils.selenium_scroll_to_bottom(driver)
                    if page_len == prev_page_len:
                        if tries >= 2:
                            raise PageEndException()
                        if prev_post:
                            _utils.selenium_scroll_into_view(driver,
                                                             prev_post)
                        tries += 1
                    else:
                        tries = 0
                    prev_page_len = page_len
                if post:
                    break

            if post:
                try:
                    post = post.find_element_by_css_selector(
                        'div.cxmmr5t8.oygrvhab.hcukyx3x.c1et5uql.ii04i59q'
                    )
                    post = post.find_element_by_xpath('..')
                except NoSuchElementException:
                    continue
                elems = \
                    post.find_elements_by_css_selector('div[role="button"]')
                for elem in elems:
                    try:
                        if elem.text == "See more":
                            if not silent:
                                print('See more')
                            for try_ in range(3):
                                action = webdriver.common.action_chains \
                                                         .ActionChains(driver)
                                action.move_to_element_with_offset(elem, 3, 3)
                                action.perform()
                                try:
                                    elem.click()
                                    break
                                except ElementClickInterceptedException:
                                    _utils.selenium_scroll_by(driver, 0, 100)
                            else:
                                post = None
                                break
                            while True:
                                try:
                                    WebDriverWait(driver, 10) \
                                        .until(EC.staleness_of(elem))
                                    break
                                except TimeoutException:
                                    print('WARNING: Timeout while post '
                                          'expanding. Retrying...')
                    except StaleElementReferenceException:
                        pass
                if not post:
                    break
                try:
                    page = post.get_attribute('innerHTML')
                    elems = post.find_elements_by_css_selector(
                        'div.cxmmr5t8.oygrvhab.hcukyx3x.c1et5uql.ii04i59q'
                    )
                except StaleElementReferenceException:
                    continue
                #text = ''.join(x.text for x in elems if x.text).strip()
                text = ''
                for elem in elems:
                    #print('[' + elem.text + ']')
                    elem = elem.find_elements_by_xpath('./div')
                    for elem_ in elem:
                        text_ = re2.sub(' ', elem_.text.replace('\n', '')) \
                                   .strip()
                        #print('{' + text_ + '}')
                        if text_:
                            text += text_ + '\n'
                #text = unescape(text).replace('\u200b', '') \
                #                     .replace('\ufeff', '') \
                #                     .replace('й', 'й').replace('ё', 'ё') \
                #                     .replace('\n\n', '\n').strip()
                text = _utils_add.norm_text2(text).replace('\n\n', '\n')
                if not silent:
                    print(text)
                text0 = re0.sub('', text)
                text1 = re1.sub('', text0)
                if text0 and len(text1) / len(text0) >= .9:
                    num_words = len([x for x in re4.sub('', text).split()
                                       if re5.sub('', x)])
                    if not silent:
                        print('<russian>')
                        print(num_words)
                    if num_words >= min_words and num_words <= max_words:
                        break
                elif not silent:
                    print('<foreign>')
                page, text = None, None

    except PageEndException:
        pass

    if need_quit:
        driver.quit()
    return text, page

def get_comment_authors(page_url, num_authors=10, depth=_utils.SEARCH_DEPTH,
                        post_limit=_utils.POST_LIMIT, authors_ignore=None,
                        driver=None, cookies=None, silent=False):
    if not silent:
        print('START', page_url)
    if driver:
        _utils.selenium_open_new_window(driver, page_url)
    else:
        driver = init(cookies)
        driver.get(page_url)
    authors = OrderedDict()
    if authors_ignore is None:
        authors_ignore = OrderedDict()
    authors_ignore[page_url] = 1

    class PageEndException(Exception):
        pass

    class AuthorsEnoughException(Exception):
        pass

    try:
        labels = set()
        post, prev_page_len = None, -1
        prev_post = None
        for post_no in range(1, post_limit + 1):
            tries = 0
            while True:
                if not silent:
                    print('post #{}...'.format(post_no))
                post = None
                posts = driver.find_elements_by_css_selector(
                    'div[aria-labelledby]'
                )
                if not silent:
                    print(len(posts))
                for post_ in posts:
                    label = post_.get_attribute('aria-labelledby')
                    #print(label, labels)
                    if label not in labels:
                        labels.add(label)
                        post = prev_post = post_
                        tries = 0
                        break
                else:
                    if not silent:
                        print('post #{} is not found'.format(post_no))
                    page_len = _utils.selenium_scroll_to_bottom(driver)
                    if page_len == prev_page_len:
                        if tries >= 2:
                            raise PageEndException()
                        if prev_post:
                            _utils.selenium_scroll_into_view(driver,
                                                             prev_post)
                        tries += 1
                    else:
                        tries = 0
                    prev_page_len = page_len
                if post:
                    break

            if post:
                comment_elems, author_elems = set(), set()
                pass_no, need_more = 0, True
                while need_more:
                    need_more = False
                    pass_no += 1
                    if not silent:
                        print('post {}, pass {}'.format(post_no, pass_no))
                    for elem in (
                        x for x in post.find_elements_by_tag_name('a')
                          if x not in author_elems
                    ):
                        author_elems.add(elem)
                        author = elem.get_attribute('href')
                        #print('[[[ author =', author, ']]]')
                        if author and author.startswith(ROOT_URL) \
                       and 'comment_id=' in author:
                            if author.startswith(ROOT_URL
                                               + '/profile.php?id='):
                                pos = author.find('&')
                            else:
                                pos = author.find('?')
                            if pos > 0:
                                author = author[:pos]
                            if author not in authors_ignore and not (
                                author.endswith('.php')
                             or author.endswith('/')
                            ):
                                #print(author)
                                if author[len(ROOT_URL) + 1:].find('/') < 0:
                                    try:
                                        author_name = \
                                            elem.find_element_by_tag_name(
                                                'span'
                                            ).text
                                        if not silent:
                                            print(author_name, author)
                                        authors_ignore[author] = 1
                                        if depth > 1:
                                            authors.update(
                                                get_comment_authors(
                                                    author,
                                                    num_authors=num_authors
                                                              - len(authors),
                                                    depth=depth - 1,
                                                    post_limit=post_limit,
                                                    authors_ignore=\
                                                        authors_ignore,
                                                    driver=driver,
                                                    #cookies=\
                                                    #    driver.get_cookies()
                                                    silent=silent
                                            ))
                                        else:
                                            authors[author] = author_name
                                        if len(authors) >= num_authors:
                                            raise AuthorsEnoughException()
                                    except NoSuchElementException:
                                        pass

                    for elem in (
                        x for x in post.find_elements_by_tag_name('span')
                          if x not in comment_elems
                    ):
                        comment_elems.add(elem)
                        try:
                            text = elem.text
                            #print('[', text, ']')
                            if (text.startswith('View') and (
                                'more comment' in text
                             or 'more repl' in text
                            )) or ('replied' in text and 'repl' in text):
                                if not silent:
                                    print('    [', text, ']')
                                need_more = True
                                action = webdriver.common.action_chains \
                                                         .ActionChains(driver)
                                action.move_to_element_with_offset(elem, 5, 5)
                                action.perform()
                                tries = 0
                                while True:
                                    try:
                                        elem.click()
                                        WebDriverWait(driver, 10) \
                                            .until(EC.staleness_of(elem))
                                        if tries:
                                            print()
                                        break
                                    except TimeoutException:
                                        print('\rWARNING: Comments loading '
                                              'timeout. Retrying...', end='')
                                        if tries >= 2:
                                            print('\rWARNING: Comments loading '
                                                  'timeout. Skipped    ')
                                            break
                                        tries += 1
                        except:
                            pass

    except (PageEndException, AuthorsEnoughException):
        pass

    _utils.selenium_close_window(driver)
    if not silent:
        print(authors)
        print(len(authors))
    return list(authors.items())[:num_authors]
