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
COOKIES_FN = '_twitter.cookies.txt'
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
        _utils.selenium_click(driver, elem,
            timeout_warning='WARNING: Login timeout. Retrying...'
        )
#        with open(COOKIES_FN, 'wt', encoding='utf-8') as f:
#            f.write(json.dumps(driver.get_cookies()))

def init(cookies=None, silent=False):
    driver = _utils.selenium_init(silent)
    #login(driver, LOGIN, PASSWORD, cookies)
    return driver

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
def get_post_text(page_url, min_words=20, max_words=200, post_limit=100,
                  driver=None, cookies=None, silent=False):
    need_quit = False
    if not silent:
        print('START', page_url)
    if not driver:
        driver = init(cookies)
        need_quit = True
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
                        text0 = re0.sub('', text)
                        text1 = re1.sub('', text0)
                        if not silent:
                            print(text)
                        if text0 and len(text1) / len(text0) >= .9:
                            num_words = len(text.split())
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

def get_comment_authors(page_url, num_authors=10, depth=2, post_limit=20,
                        authors_ignore=None, driver=None, cookies=None,
                        silent=False):
    if not silent:
        print('START', page_url)
    if driver:
        _utils.selenium_open_new_window(driver, page_url)
    else:
        driver = init(cookies)
        driver.get(page_url)
    time.sleep(LOAD_TIMEOUT)
    authors = OrderedDict()
    authors_ignore = set(authors_ignore if authors_ignore else [])
    authors_ignore.add(page_url)

    class PageEndException(Exception):
        pass

    class AuthorsEnoughException(Exception):
        pass

    try:
        labels = set()
        post, prev_page_len = None, -1
        for post_no in range(1, post_limit + 1):
            posts, tries = None, 0
            while True:
                try:
                    if not silent:
                        print('post #{}...'.format(post_no))
                    post = None
                    if not posts:
                        posts = driver.find_elements_by_css_selector(
                            #'article[role="article"]'
                            'div[data-testid="tweet"]'
                        )
                        if not silent:
                            print(len(posts))
                    post_no_ = 0
                    for post_no_, post_ in enumerate(posts):
                        try:
                            post_ = post_.find_element_by_xpath(
                                './div/div/div/div/span[@class="css-901oao css-16my406 r-1qd0xha r-ad9z0x r-bcqeeo r-qvutc0"]'
                             #' | ./div/div/div/div/span[@class="css-901oao css-16my406 r-4qtqp9 r-ip8ujx r-sjv1od r-zw8f10 r-bnwqim r-h9hxbl"]'
                            )
                        except NoSuchElementException:
                            continue
                        _utils.selenium_scroll_into_view(driver, post_)
                        label = post_.text
                        #print(label, labels)
                        if label not in labels:
                            labels.add(label)
                            post = post_
                            tries = 0
                            break
                    else:
                        if not silent:
                            print('post #{} is not found'.format(post_no))
                        page_len = _utils.selenium_scroll_to_bottom(driver)
                        if not silent:
                            print('page_len =', page_len)
                        if page_len == prev_page_len:
                            if tries >= 2:
                                raise PageEndException()
                            tries += 1
                        else:
                            tries = 0
                        prev_page_len = page_len
                        posts = None
                        continue
                    if post_no_:
                        posts = posts[:post_no_]
                except StaleElementReferenceException:
                    _utils.selenium_scroll_to_bottom(driver)
                    posts = None
                if post:
                    break

            if post:
                _utils.selenium_scroll_into_view(driver, post)
                _utils.selenium_scroll_by(driver, 0, -100)
                _utils.selenium_ctrl_click(driver, post)
                #post.click()
                _utils.selenium_scroll_to_bottom(driver)

                comment_elems, author_elems = set(), set()
                while True:
                    comments = driver.find_elements_by_css_selector(
                        #'article[role="article"]'
                        'div[data-testid="tweet"]'
                    )
                    if not silent:
                        print(len(comments))
                    comment = None
                    retry = False
                    for comment_ in comments:
                        if not silent:
                            print('COMMENT ', end='')
                        try:
                            link = comment_.find_element_by_xpath(
                                './div/div/div/div/div/div/a[@role="link"]'
                            )
                        except NoSuchElementException:
                            if not silent:
                                print('not found')
                            continue
                        except StaleElementReferenceException:
                            retry = True
                            break
                        if not silent:
                            print('found')
                        comment = comment_
                        _utils.selenium_scroll_into_view(driver, link)
                        author = link.get_attribute('href')
                        author_name = link.find_element_by_tag_name('span') \
                                          .text
                        if not silent:
                            print(author_name, author)
                        if author not in authors_ignore:
                            authors_ignore.add(author)
                            if depth > 1:
                                authors.update(
                                    get_comment_authors(
                                        author,
                                        num_authors=\
                                            num_authors - len(authors),
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
                            if not silent:
                                print('len(authors) =', len(authors))
                            if len(authors) >= num_authors:
                                raise AuthorsEnoughException()
                    if retry:
                        if not silent:
                           print('RETRY')
                        continue
                    if comment:
                        elem = comment.find_element_by_xpath(
                            '..' + ('/..' * 7)
                        )
                        try:
                            elemMore = comment.find_element_by_css_selector(
                                'div[class="css-18t94o4 css-1dbjc4n r-1777fci r-1jayybb r-1ny4l3l r-o7ynqc r-6416eg r-13qz1uu"]'
                            )
                            if not silent:
                                print('MORE')
                            _utils.selenium_click(elemMore, max_tries=5,
                                timeout_warning='WARNING: Comments loading '
                                                'timeout. Retrying...'
                            )
                        except NoSuchElementException:
                            break
                    else:
                        break

                _utils.selenium_close_window(driver)
                #if not silent:
                #    print('BACK')
                #back = driver.find_element_by_css_selector(
                #    'div[class="css-18t94o4 css-1dbjc4n '
                #    'r-1niwhzg r-42olwf r-sdzlij r-1phboty r-rs99b7 r-1w2pmg '
                #    'r-1vuscfd r-53xb7h r-1ny4l3l r-mk0yit r-o7ynqc r-6416eg '
                #    'r-lrvibr"]'
                #)
                #back.click()

    except (PageEndException, AuthorsEnoughException):
        pass

    _utils.selenium_close_window(driver)
    if not silent:
        print(authors)
        print(len(authors))
    return list(authors.items())[:num_authors]

def get_trend_authors(trend, num_authors=10, skip_first=0,
                      authors_ignore=None, driver=None, cookies=None,
                      silent=False):
    page_url = ROOT_URL + '/search?q=' + trend + '&src=typed_query'
    need_quit = False
    if not silent:
        print('START', page_url)
    if not driver:
        driver = init(cookies)
        need_quit = True
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
                            _utils.selenium_click(driver, btn, max_tries=3)  # exit with error if timeout
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
