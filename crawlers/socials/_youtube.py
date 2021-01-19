#-*- encoding: utf-8 -*-

from collections import OrderedDict
import json
import os
import random
import re
from selenium import webdriver
from selenium.common.exceptions \
    import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import time
from urllib.parse import urlparse

###
import sys
sys.path.append('../')
###
from _utils_add import get_url
import _utils


ROOT_URL = 'https://www.youtube.com'
LOAD_TIMEOUT = 3
NUM_ITEMS = 200

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re2 = re.compile('"url":"(/[^"]+/videos)"')
re3 = re.compile('<link itemprop="url" href="([^">]+)">'
                 '<link itemprop="name" content="([^">]+)">')
re4 = re.compile(r'#\b\S+\b')
re5 = re.compile(r'\W')
def crawl(channels_queue, min_words=_utils.MIN_CHUNK_WORDS,
          max_words=_utils.MAX_CHUNK_WORDS, post_limit=_utils.POST_LIMIT,
          channels_ignore=None, authors_ignore=None, driver=None,
          cookies=None, silent=True):
    need_quit = False
    if not driver:
        driver = _utils.selenium_init(silent=False)
        need_quit = True
    if channels_ignore is None:
        channels_ignore = OrderedDict()
    if authors_ignore is None:
        authors_ignore = OrderedDict()
    channel_names_ignore = set(channels_ignore.values())

    class LoopBreakException(Exception):
        pass

    while True:
        if not channels_queue:
            break
        page = text = None
        isrussian = False
        # search for link to VIDEOS folder
        channel = channels_queue.popitem(last=False)
        url = channel[0]
        if not silent:
            print('START', url, end='')
        html = get_url(url).text
        match = re2.search(html)
        if match:
            path = match.group(1)
            #page_url = '{0.scheme}://{0.netloc}{1}'.format(urlparse(url), path)
            page_url = ROOT_URL + path
        else:
            page_url = url.replace('/channel/', '/c/', 1) + '/videos'
            url = url.replace('/channel/', '/user/', 1)
            html = get_url(url).text
            match = re2.search(html)
            if match:
                path = match.group(1)
                #page_url = '{0.scheme}://{0.netloc}{1}'.format(urlparse(url), path)
                page_url = ROOT_URL + path
            else:
                url = None
        if not silent:
            print(' ->', page_url, end='')

        driver.delete_all_cookies()

        # get random video of first NUM_ITEMS
        driver.get(page_url)
        try:
            channel_url = \
                driver.find_element_by_css_selector('link[rel="canonical"]') \
                      .get_attribute('href')
            channel_name = driver.find_element_by_id('inner-header-container') \
                                 .find_element_by_id('channel-name') \
                                 .find_element_by_id('text').text
        except NoSuchElementException:
            if not silent:
                print(': NOT FOUND')
            yield None, None, None  # possibility to save new status
            continue
        if not silent:
            print()
        if url:
            channels_ignore[url] = channel_name
        channels_ignore[channel_url] = channel_name
        channel_names_ignore.add(channel_name)
        elem = driver.find_element_by_id('contents')
        try:
            elem_items = elem.find_element_by_id('items')
        except NoSuchElementException:
            yield None, None, None  # possibility to save new status
            continue
        elem_cont = elem.find_element_by_id('continuations')
        items, num_items = None, 0
        while True:
            items = elem_items.find_elements_by_xpath(
                './ytd-grid-video-renderer'
            )
            num_items_ = len(items)
            if num_items_ == num_items:
                break
            num_items = num_items_
            if num_items >= NUM_ITEMS:
                break
            _utils.selenium_scroll_into_view(driver, elem_cont)
        # abandon this channel if there is no comments
        # (and not to scan related videos because they are probably the same)
        if not items:
            yield None, None, None  # possibility to save new status
            continue
        item = items[random.randint(0, num_items - 1)]
        elem = item.find_element_by_id('thumbnail')
        url = elem.get_attribute('href')
        driver.get(url)

        # search for a comment of a size in given limits
        tries_ = 0
        try:
            while True:
                try:
                    _utils.selenium_click(driver,
                                          visible_elem=(By.ID, 'ytd-player'),
                                          max_tries=3)
                    _utils.selenium_remove(driver,
                                           driver.find_element_by_id('ytd-player'))
                    raise LoopBreakException()
                except TimeoutException:
                    try:
                        _utils.selenium_click(driver,
                                              visible_elem=(By.ID,
                                                            'error-screen'),
                                              max_tries=1)
                        raise NoSuchElementException()
                    except TimeoutException:
                        if tries_ % 10 == 0:
                            print("Can't find a video")
                        tries_ += 1
        except NoSuchElementException:
            yield None, None, None  # possibility to save new status
            continue
        except LoopBreakException:
            pass
        try:
            _utils.selenium_click(driver, visible_elem=(By.ID, 'sections'),
                                  max_tries=10)
        except TimeoutException:
            yield None, None, None  # possibility to save new status
            continue
        elem = driver.find_element_by_id('sections')
        elem_items = elem.find_element_by_id('contents')
        elem_cont = elem.find_element_by_id('continuations')
        items, num_items = None, 0
        def notactive(elem):
            return elem.get_attribute('active') is None
        while True:
            _utils.selenium_scroll_into_view(driver, elem_cont)
            WebDriverWait(elem_cont, 10).until(notactive)
            items = elem_items.find_elements_by_xpath(
                './ytd-comment-thread-renderer'
            )
            num_items_ = len(items)
            if num_items_ == num_items:
                break
            num_items = num_items_
            if num_items >= NUM_ITEMS:
                break
        if not items:
            yield None, None, None  # possibility to save new status
            continue
        _utils.selenium_scroll_to_top(driver)
        for item in reversed(items):
            try:
                elem = item.find_element_by_id('author-comment-badge')
            except NoSuchElementException:
                continue
            elem = item.find_element_by_id('author-text')
            author_href = elem.get_attribute('href')
            author_name = elem.get_attribute('text').strip()
            if author_href in authors_ignore:
                continue
            text_elem = item.find_element_by_id('content-text')
            text = text_elem.text
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
                isrussian = True
                if not silent:
                    print('<russian>')
                    print(num_words)
                if num_words >= min_words \
               and num_words <= max_words:
                    page = text_elem.get_attribute('innerHTML')
                    authors_ignore[author_href] = author_name
                    break
            elif not silent:
                print('<foreign>')
            text = None
        if not isrussian:
            yield None, None, None  # possibility to save new status
            continue

        # search in related videos for new channels
        elem = driver.find_element_by_id('secondary-inner')
        elem_cont = elem.find_element_by_id('continuations')
        elem_items = elem.find_element_by_id('items')
        items, num_items = [], 0
        while True:
            items = elem_items.find_elements_by_xpath(
                './/ytd-compact-video-renderer'
            )
            num_items_ = len(items)
            if num_items_ == num_items:
                break
            num_items = num_items_
            if num_items >= NUM_ITEMS:
                break
            try:
                elem_cont_flag = elem_items.find_element_by_xpath(
                    '..//ytd-continuation-item-renderer'
                )
            except NoSuchElementException:
                break
            _utils.selenium_scroll_into_view(driver, elem_cont)
        if not silent:
            print('found', num_items, 'relative videos')
        for item in items:
            channel_name = item.find_element_by_id('channel-name') \
                               .find_element_by_id('text')
            if channel_name in channel_names_ignore:
                continue
            elem = item.find_element_by_id('thumbnail')
            url = elem.get_attribute('href')
            html = get_url(url).text
            match = re3.search(html)
            if not match:
                continue
            channel_url, channel_name = match.groups()
            channel_url = channel_url.replace('http:', 'https:')
            if not silent:
                print('   ', channel_url, channel_name, end='')
            if channel_url not in channels_ignore:
                channels_queue[channel_url] = channel_name
                channel_names_ignore.add(channel_name)
            elif not silent:
                print(': IGNORED', end='')
            if not silent:
                print()

        # return
        yield text, page, driver.current_url

    if need_quit:
        driver.quit()
