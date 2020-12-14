#-*- encoding: utf-8 -*-

from collections import OrderedDict
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions \
    import ElementClickInterceptedException, NoSuchElementException, \
           TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time


LOGIN_URL = 'https://facebook.com'
ROOT_URL = 'https://www.facebook.com'
CREDENTIALS_FN = '_facebook.credentials.txt'
CREDENTIALS = ['email', 'password']

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

creds = dict(parse_credentials(CREDENTIALS_FN))
assert len(creds) == 2, 'ERROR: invalid credentials file ' + CREDENTIALS_FN
LOGIN, PASSWORD = [creds.get(x) for x in CREDENTIALS]
del creds

def login(driver, login, password, cookies=None):
    driver.get(LOGIN_URL)
    driver.maximize_window()
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
    login(driver, LOGIN, PASSWORD, cookies)
    return driver

def get_post_text(page_url, min_words=20, max_words=200, post_limit=100,
                  driver=None, cookies=None, silent=False):
    re0 = re.compile(r'\W|\d')
    re1 = re.compile(r'[^ЁА-Яёа-я]')
    re2 = re.compile(r'\s+')
    if not silent:
        print('START', page_url)
    if driver:
        driver.execute_script('window.open("{}");'.format(page_url))
        driver.switch_to.window(driver.window_handles[-1])
    else:
        driver = init(cookies)
        driver.get(page_url)
    page, text = None, None

    class PageEndException(Exception):
        pass

    try:
        labels = set()
        post, prev_page_len = None, -1
        for post_no in range(1, post_limit + 1):
            tries = 0
            while True:
                if not silent:
                    print('post #{}...'.format(post_no))
                post = None
                '''
                try:
                    post = driver.find_element_by_css_selector(
                        'div[aria-posinset="{}"]'.format(post_no)
                    )
                    break
                except NoSuchElementException:
                    if not silent:
                        print('post #{} is not found'.format(post_no))
                    page_len = driver.execute_script(
                        'window.scrollTo(0, document.body.scrollHeight);'
                        'var lenOfPage=document.body.scrollHeight;'
                        'return lenOfPage;'
                    )
                    time.sleep(5)  # TODO: replace to some load detection
                                   #       method
                    if page_len == prev_page_len:
                        raise PageEndException()
                    prev_page_len = page_len
                '''
                posts = driver.find_elements_by_css_selector(
                    'div[aria-labelledby]'
                )
                if not silent:
                    print(len(posts))
                for post_ in posts:
                    #print(post_.get_attribute('aria-describedby'))
                    #print(post_.get_attribute('aria-labelledby'))
                    #attrs = driver.execute_script('var items = {}; for (index = 0; index < arguments[0].attributes.length; ++index) { items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value }; return items;', post_)
                    #print(attrs)
                    #exit()
                    label = post_.get_attribute('aria-labelledby')
                    #print(label, labels)
                    if label not in labels:
                        labels.add(label)
                        post = post_
                        tries = 0
                        break
                else:
                    if not silent:
                        print('post #{} is not found'.format(post_no))
                    page_len = driver.execute_script(
                        'window.scrollTo(0, document.body.scrollHeight);'
                        'var lenOfPage=document.body.scrollHeight;'
                        'return lenOfPage;'
                    )
                    time.sleep(5)  # TODO: replace to some load detection
                                   #       method
                    if page_len == prev_page_len:
                        if tries >= 2:
                            raise PageEndException()
                        tries += 1
                    else:
                        tries = 0
                    prev_page_len = page_len
                if post:
                    break

            if post:
                #oajrlxb2 g5ia77u1 qu0x051f esr5mh6w e9989ue4 r7d6kgcz
                #rq0escxv nhd2j8a9 nc684nl6 p7hjln8o kvgmc6g5 cxmmr5t8
                #oygrvhab hcukyx3x jb3vyjys rz4wbd8a qt6c0cv9 a8nywdso
                #i1ao9s8h esuyzwwr f1sip0of lzcic4wl oo9gr5id gpro0wi8
                #lrazzd5p
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
                    if elem.text == "See more":
                        if not silent:
                            print('more')
                        action = webdriver.common.action_chains \
                                                 .ActionChains(driver)
                        action.move_to_element_with_offset(elem, 5, 5)
                        action.perform()
                        while True:
                            try:
                                elem.click()
                                break
                            except ElementClickInterceptedException:
                                driver.execute_script(
                                    'window.scrollBy(0, 100);'
                                )
                        while True:
                            try:
                                WebDriverWait(driver, 10) \
                                    .until(EC.staleness_of(elem))
                                break
                            except TimeoutException:
                                print('WARNING: Timeout while post '
                                      'expanding. Retrying...')
                page = post.get_attribute('innerHTML')
                elems = post.find_elements_by_css_selector(
                    'div.cxmmr5t8.oygrvhab.hcukyx3x.c1et5uql.ii04i59q'
                )
                #text = ''.join(x.text for x in elems if x.text).strip()
                text = ''
                for elem in elems:
                    #print('[' + elem.text + ']')
                    elem = elem.find_elements_by_xpath('.//div')
                    for elem_ in elem:
                        text_ = re2.sub(' ', elem_.text.replace('\n', '')) \
                                   .strip()
                        #print('{' + text_ + '}')
                        if text_:
                            text += text_ + '\n'
                    #if elem.tag_name == 'div':
                    #    text += '\n' + elem.text.replace('\n', '').strip() \
                    #          + '\n'
                    #else:
                    #    text += elem.text
                text = text.replace('\n\n', '\n').strip()
                text0 = re0.sub('', text)
                text1 = re1.sub('', text0)
                if not silent:
                    print(text)
                if text0 and len(text1) / len(text0) >= .9:
                    num_words = len(text.split())
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

    if len(driver.window_handles) > 1:
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
    else:
        driver.quit()
    return text, page

def get_comment_authors(page_url, num_authors=10, depth=1, post_limit=20,
                        authors_ignore=None, driver=None, cookies=None,
                        silent=False):
    if not silent:
        print('START', page_url)
    if driver:
        driver.execute_script('window.open("{}");'.format(page_url))
        driver.switch_to.window(driver.window_handles[-1])
    else:
        driver = init(cookies)
        driver.get(page_url)
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
            tries = 0
            while True:
                if not silent:
                    print('post #{}...'.format(post_no))
                post = None
                '''
                try:
                    post = driver.find_element_by_css_selector(
                        'div[aria-posinset="{}"]'.format(post_no)
                    )
                    break
                except NoSuchElementException:
                    if not silent:
                        print('post #{} is not found'.format(post_no))
                    page_len = driver.execute_script(
                        'window.scrollTo(0, document.body.scrollHeight);'
                        'var lenOfPage=document.body.scrollHeight;'
                        'return lenOfPage;'
                    )
                    time.sleep(5)  # TODO: replace to some load detection
                                   #       method
                    if page_len == prev_page_len:
                        raise PageEndException()
                    prev_page_len = page_len
                '''
                posts = driver.find_elements_by_css_selector(
                    'div[aria-labelledby]'
                )
                if not silent:
                    print(len(posts))
                for post_ in posts:
                    #print(post_.get_attribute('aria-describedby'))
                    #print(post_.get_attribute('aria-labelledby'))
                    #attrs = driver.execute_script('var items = {}; for (index = 0; index < arguments[0].attributes.length; ++index) { items[arguments[0].attributes[index].name] = arguments[0].attributes[index].value }; return items;', post_)
                    #print(attrs)
                    #exit()
                    label = post_.get_attribute('aria-labelledby')
                    #print(label, labels)
                    if label not in labels:
                        labels.add(label)
                        post = post_
                        tries = 0
                        break
                else:
                    if not silent:
                        print('post #{} is not found'.format(post_no))
                    page_len = driver.execute_script(
                        'window.scrollTo(0, document.body.scrollHeight);'
                        'var lenOfPage=document.body.scrollHeight;'
                        'return lenOfPage;'
                    )
                    time.sleep(5)  # TODO: replace to some load detection
                                   #       method
                    if page_len == prev_page_len:
                        if tries >= 2:
                            raise PageEndException()
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
                                        authors_ignore.add(author)
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
                                while True:
                                    try:
                                        elem.click()
                                        WebDriverWait(driver, 10) \
                                            .until(EC.staleness_of(elem))
                                        break
                                    except TimeoutException:
                                        print('WARNING: Comments loading '
                                              'timeout. Retrying...')
                        except:
                            pass

    except (PageEndException, AuthorsEnoughException):
        pass

    if len(driver.window_handles) > 1:
        driver.close()
        driver.switch_to.window(driver.window_handles[-1])
    else:
        driver.quit()
    if not silent:
        print(authors)
        print(len(authors))
    return list(authors.items())[:num_authors]
