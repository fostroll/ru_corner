#-*- encoding: utf-8 -*-

from collections import OrderedDict
from html import unescape
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

import _utils


LOGIN_URL = 'https://instagram.com'
ROOT_URL = 'https://www.instagram.com'
CREDENTIALS_FN = '_instagram.credentials.txt'
CREDENTIALS = ['username', 'password']

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
        WebDriverWait(driver, 10) \
            .until(EC.presence_of_element_located((By.NAME, 'username')))
        driver.find_element_by_name('username').send_keys(login)
        driver.find_element_by_name('password').send_keys(password)
        driver.find_element_by_css_selector('button[type="submit"]').click()
        while True:
            try:
                WebDriverWait(driver, 10) \
                    .until(EC.presence_of_element_located(
                        (By.CSS_SELECTOR,
                         'button[class="sqdOP  L3NKy   y3zKF     "]')
                    ))
                driver.find_element_by_css_selector(
                    'button[class="sqdOP  L3NKy   y3zKF     "]'
                ).click()
                time.sleep(3)
                break
            except TimeoutException:
                print('WARNING: Login timeout. Retrying...')

def init(cookies=None, silent=False):
    driver = _utils.selenium_init(silent=silent)
    login(driver, LOGIN, PASSWORD, cookies)
    return driver

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re2 = re.compile(r'[^\S\n]+')
re3 = re.compile(r'\n+')
re4 = re.compile(r'#\b\S+\b')
re5 = re.compile(r'\W')
def get_post_text(page_url, min_words=20, max_words=200, post_limit=20,
                  driver=None, cookies=None, silent=False):
    if not silent:
        print('START', page_url)
    if not driver:
        driver = init(cookies)
    driver.get(page_url)
    link, page, text = None, None, None

    class PageEndException(Exception):
        pass

    try:
        labels = set()
        post_no, prev_page_len = 1, -1
        tries = 0
        while True:
            if not silent:
                print('post #{}...'.format(post_no))
            posts = driver.find_elements_by_xpath(
                '//article/div/div/div/div'
            )
            if not silent:
                print(len(posts))
            for post in posts:
                try:
                    if post.get_attribute('class') == 'EcJQs':
                        raise PageEndException()
                    _utils.selenium_scroll_into_view(driver, post)
                except StaleElementReferenceException:
                    break
                _utils.selenium_move_to_element(driver, post, 3)
                try:
                    label = post.find_element_by_tag_name('a') \
                                .get_attribute('href')
                except NoSuchElementException:
                    continue
                if not silent:
                    print('url', label, end=' ')
                if label in labels:
                    if not silent:
                        print('old')
                    continue
                if not silent:
                    print('new')
                labels.add(label)
                post_no += 1
                if post_no > post_limit:
                    raise PageEndException()
                tries = 0
                _utils.selenium_open_new_window(driver, label)
                try:
                    WebDriverWait(driver, 3) \
                        .until(EC.visibility_of_element_located(
                            (By.CLASS_NAME, 'XQXOT')
                        ))
                    elem = driver.find_element_by_class_name('XQXOT')
                    elem = elem.find_element_by_xpath(
                        './div[@class="ZyFrc"]/li/div/div/div[@class="C4VMK"]/span'
                    )
                except (TimeoutException, NoSuchElementException):
                    _utils.selenium_close_window(driver)
                    continue
                link = label
                page = elem.get_attribute('innerHTML')
                text = elem.text
                if not silent:
                    print(text)
                _utils.selenium_close_window(driver)
                text = re3.sub('\n', re2.sub(' ',
                    unescape(text).replace('\u200b', '') \
                                  .replace('\ufeff', '') \
                                  .replace('й', 'й').replace('ё', 'ё') \
                                  .strip()
                ))
                text0 = re0.sub('', re4.sub('', text))
                text1 = re1.sub('', text0)
                if not silent:
                    print(text)
                if text0 and len(text1) / len(text0) >= .9:
                    num_words = len([x for x in re4.sub('', text).split()
                                       if re5.sub('', x)])
                    if not silent:
                        print('<russian>')
                        print(num_words)
                    if num_words >= min_words and num_words <= max_words:
                        raise PageEndException()
                elif not silent:
                    print('<foreign>')
                link, page, text = None, None, None
            else:
                if not silent:
                    print('post #{} is not found'.format(post_no))
                page_len = _utils.selenium_scroll_to_bottom(driver)
                if page_len == prev_page_len:
                    if tries >= 2:
                        raise PageEndException()
                    tries += 1
                else:
                    tries = 0
                prev_page_len = page_len

    except PageEndException:
        pass

    return text, page, link

def get_likers(page_url, num_likers=10, skip=(0, 0), post_limit=20,
               likers_ignore=None, driver=None, cookies=None, silent=False):
    if not silent:
        print('START', page_url)
    if not driver:
        driver = init(cookies)
    driver.get(page_url)
    likers = OrderedDict()
    if likers_ignore is None:
        likers_ignore = OrderedDict()
    likers_ignore[page_url] = 1

    class PageEndException(Exception):
        pass

    class LikersEnoughException(Exception):
        pass

    try:
        labels = set()
        post_no, prev_page_len = 1, -1
        tries = 0
        while True:
            if not silent:
                print('post #{}...'.format(post_no))
            posts = driver.find_elements_by_xpath(
                '//article/div/div/div/div'
            )
            if not silent:
                print(len(posts))
            for post in posts:
                try:
                    if post.get_attribute('class') == 'EcJQs':
                        raise PageEndException()
                    _utils.selenium_scroll_into_view(driver, post)
                except StaleElementReferenceException:
                    break
                _utils.selenium_move_to_element(driver, post, 3)
                try:
                    label = post.find_element_by_tag_name('a') \
                                .get_attribute('href')
                except NoSuchElementException:
                    continue
                if not silent:
                    print('url', label, end=' ')
                if label in labels:
                    if not silent:
                        print('old')
                    continue
                if not silent:
                    print('new')
                labels.add(label)
                post_no += 1
                if post_no > post_limit:
                    raise PageEndException()
                tries = 0
                try:
                   likelem = post.find_element_by_css_selector(
                       'span[class="_1P1TY coreSpriteHeartSmall"]'
                   )
                except NoSuchElementException:
                    continue
                try:
                   cnt = int(likelem.find_element_by_xpath('..')
                                    .text.strip())
                except ValueError:
                    cnt = 1000
                if cnt <= skip[0]:
                    continue
                start_liker_no = min(max(skip[0], round(cnt * skip[1])), 100)
                if not silent:
                    print(cnt, start_liker_no)
                _utils.selenium_open_new_window(driver, label)
                time.sleep(3)
                elem = driver.find_element_by_css_selector(
                    'button[class="sqdOP yWX7d     _8A5w5    "]'
                )
                css_selector = 'div[class="                     Igw0E  ' \
                               '   IwRSH        YBx95      vwCYk       ' \
                               '                                       ' \
                               '                                       ' \
                               '                          "]'
                try:
                    _utils.selenium_click(driver, elem, 
                                          visible_elem=(By.CSS_SELECTOR,
                                                        css_selector),
                                          max_tries=1)
                except TimeoutException:
                    time.sleep(60)
                    _utils.selenium_close_window(driver)
                    continue
                like_no = 0
                likers_passed = set()
                while True:
                    likers_passed_ = set()
                    likelems = driver.find_elements_by_css_selector(
                        css_selector
                    )
                    if not silent:
                        print('found {} likers'.format(len(likelems)))
                    if not likelems:
                        break
                    all_ignored = True
                    for likelem in likelems:
                        like_no += 1
                        elem = likelem.find_element_by_tag_name('a')
                        link = elem.get_attribute('href')
                        name = elem.get_attribute('title')
                        likers_passed_.add(link)
                        if link not in likers_passed:
                            all_ignored = False
                        if link in likers_ignore:
                            continue
                        likers_ignore[link] = 1
                        if not silent:
                            print('like:', link)
                        if like_no >= start_liker_no:
                            try:
                                name = \
                                    likelem.find_element_by_css_selector(
                                        'div[class="_7UhW9   xLCgt     '
                                        ' MMzan   _0PwGv         uL8Hv '
                                        '        "]'
                                ).text
                            except NoSuchElementException:
                                pass
                            likers[link] = name
                            if not silent:
                                print('   ', name)
                            if len(likers) >= num_likers:
                                _utils.selenium_close_window(driver)
                                raise LikersEnoughException()
                    if all_ignored:
                        time.sleep(60)
                        break
                    likers_passed = likers_passed_
                    _utils.selenium_scroll_into_view(driver,
                                                     likelems[-1])
                _utils.selenium_close_window(driver)
            else:
                if not silent:
                    print('post #{} is not found'.format(post_no))
                page_len = _utils.selenium_scroll_to_bottom(driver)
                if page_len == prev_page_len:
                    if tries >= 2:
                        raise PageEndException()
                    tries += 1
                else:
                    tries = 0
                prev_page_len = page_len

    except (PageEndException, LikersEnoughException):
        pass

    if not silent:
        print(likers)
        print(len(likers))
    return list(likers.items())[:num_likers]
