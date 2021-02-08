#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os
import random
import re
import time

###
import sys
sys.path.append('../')
###
import utils


SEED = 42
ROOT_URL = 'https://otzovik.com'
URL = ROOT_URL + '/lastreviews/{}/'
AUTHORS_IGNORE_FN = os.path.join(utils.PAGES_DIR, 'authors_ignore.tmp')
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'TE': 'Trailers'
}
COOKIES = {
    'csid': '4103094974',
    'guid': 'dc1ad8f971955ac140b17825109a50b3',
    'refreg': '1604482358~',
    'ROBINBOBIN': '2812f2963c1610e6a5c1621217',
    'ssid': '4103094974'
}
MIN_TEXT_LINES = 1
MIN_CHUNK_WORDS = 20
MAX_CHUNK_WORDS = 200
SILENT = False

if SEED:
    random.seed(SEED)

'''===========================================================================
Links download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n') if x]
else:
    links = []

if len(links) < utils.TEXTS_FOR_SOURCE:
    FIRST_LINK_IDS = []
    links = OrderedDict((x, 1) for x in links)
    if os.path.isfile(AUTHORS_IGNORE_FN):
        with open(AUTHORS_IGNORE_FN, 'rt', encoding='utf-8') as f:
            authors_ignore = OrderedDict(x.split('\t')
                                             for x in f.read().split('\n')
                                             if x)
    else:
        authors_ignore = OrderedDict()
    for page_no in range(1, 21):
        url = URL.format(page_no)
        res = utils.get_url(url, headers=HEADERS, cookies=COOKIES)
        while True:
            page = res.text
            res = page.split('<div class="item mshow0" data-id="')[1:]
            res_len = len(res)
            with open('1111.html', 'wt', encoding='utf-8') as f:
                f.write(page)
            if res_len != 20:
                if res_len:
                    print('WARNING: {} links on page "{}" (must be 20)'
                              .format(res_len, url))
                else:
                    match = re.search(
                        r'<img src="(/scripts/captcha/index\.php\?rand=\d+)">',
                        page
                    )
                    if match:
                        captcha_url = ROOT_URL + match.group(1)
                        print('What is the captcha on "{}"?'
                                  .format(captcha_url))
                        captcha = input('Enter a value: ')
                        res = utils.get_url(
                            url, headers=HEADERS, data={
                                'captcha_url': url.replace(ROOT_URL, ''),
                                'llllllllllllllllllllllllllllllll': captcha
                            }
                        )
                        continue
                    else:
                        assert 0, 'ERROR: No links on page "{}"!'.format(url)
            break
        need_break = False
        for rec_no, rec in enumerate(res):
            pos = rec.find('"')
            assert pos >= 0, "ERROR: Can't find data_id on {}, record {}" \
                                 .format(url, rec_no)
            link_id = rec[:pos]
            link = '{}/review_{}.html'.format(ROOT_URL, link_id)
            FIRST_LINK_IDS.append(int(link_id))
            if link in links:
                continue
            rec = rec[pos:]
            pos = rec.find('<a class="user-login')
            assert pos >= 0, "ERROR: Can't find user-login on {}, record {}" \
                                 .format(url, rec_no)
            rec = rec[pos:]
            token = 'href="/profile/'
            pos = rec.find(token)
            assert pos >= 0, "ERROR: Can't find profile0 on {}, record {}" \
                                 .format(url, rec_no)
            rec = rec[pos + len(token):]
            pos = rec.find('"')
            assert pos >= 0, "ERROR: Can't find profile1 on {}, record {}" \
                                 .format(url, rec_no)
            author = '{}/profile/{}'.format(ROOT_URL, rec[:pos])
            if author in authors_ignore:
                continue
            rec = rec[pos:]
            pos = rec.find('>')
            assert pos >= 0, "ERROR: Can't find profile2 on {}, record {}" \
                                 .format(url, rec_no)
            rec = rec[pos + 1:]
            pos = rec.find('<')
            assert pos >= 0, "ERROR: Can't find profile3 on {}, record {}" \
                                 .format(url, rec_no)
            author_name = rec[:pos]
            authors_ignore[author] = author_name
            links[link] = 1
            if len(links) >= utils.TEXTS_FOR_SOURCE * 2:
                need_break = True
                break
        break  # after page 1
        if need_break:
            break
    FIRST_LINK_ID = min(*FIRST_LINK_IDS)
    links = ['{}/review_{}.html'.format(ROOT_URL, x)
                 for x in range(FIRST_LINK_ID - utils.TEXTS_FOR_SOURCE * 100,
                                FIRST_LINK_ID)]
    '''
    with open(AUTHORS_IGNORE_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join('\t'.join(x) for x in authors_ignore.items()))
    links = list(links)
    '''
    if len(links) >= utils.TEXTS_FOR_SOURCE:
        random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))

'''===========================================================================
Texts download and parse
==========================================================================='''
MAX_PAGE = 10000
page_fns = utils.get_file_list(utils.PAGES_DIR, MAX_PAGE)
start_link_idx = int(os.path.split(sorted(page_fns)[-1])[-1]
                         .replace(utils.DATA_EXT, '')) \
                     if len(page_fns) > 0 else \
                 0
texts_total = 0

re0 = re.compile(r'\W|\d')
re1 = re.compile(r'[^ЁА-Яёа-я]')
re5 = re.compile(r'\W')
re10 = re.compile(r'<h1>((?:.|\n)*?)</h1>')
re11 = re.compile(r'<div class="review-body description" itemprop="description">((?:.|\n)+)$')
re12 = re.compile(r'<(?P<tag>\S+)[^>]*>.*?</(?P=tag)>')
re13 = re.compile(r'<(?:[^/].*)?>')
need_enter = False
for link_no, link in enumerate(links, start=1):
    if texts_total >= utils.TEXTS_FOR_SOURCE:
        break
    page_fn = utils.get_data_path(utils.PAGES_DIR, MAX_PAGE, link_no)
    text_fn = utils.get_data_path(utils.TEXTS_DIR, MAX_PAGE, link_no)
    page = None
    #link = 'https://otzovik.com/review_11427160.html'
    if link_no > start_link_idx:
        time.sleep(2)
        res = utils.get_url(link, headers=HEADERS, cookies=COOKIES)
        page = res.text
        with open('1111.html', 'wt', encoding='utf-8') as f:
            f.write(page)
        if page.find('<title>Ошибка: Страница не найдена!</title>') > 0:
            continue
    else:
        if not os.path.isfile(page_fn):
            continue
        if os.path.isfile(text_fn):
            texts_total += 1
            continue
        with open(page_fn, 'rt', encoding='utf-8') as f:
            link = f.readline().rstrip()
            page = f.read()
    match = re10.search(page)
    assert match, "ERROR: Can't find header on page {}".format(link)
    header = utils.norm_text2(match.group(1))
    match = re11.search(page)
    assert match, "ERROR: Can't find review on page {}".format(link)
    text = match.group(1)
    text = re12.sub('', text).replace('\n', '').replace('<br>', '\n') \
                             .replace('<br/>', '\n').replace('<br />', '\n')
    text = re13.sub('', text)
    pos = text.find('<')  ## </div>
    if pos >= 0:
        text = text[:pos]
    text = utils.norm_text2(text)
    lines = [header] + [x for x in (x.strip() for x in text.split('\n')) if x]
    res, text = False, None
    while len(lines) >= MIN_TEXT_LINES:
        text = '\n'.join(lines)
        text0 = re0.sub('', text)
        text1 = re1.sub('', text0)
        if any(x in 'ЀЂЃЄЅІЇЈЉЊЋЌЍЎЏѐђѓєѕіїјљњћќѝўџѠѡѢѣѤѥѦѧѨѩѪѫѬѭѮѯѰѱѲѳѴѵѶѷѸѹ'
                    'ѺѻѼѽѾѿҀҁ҂҃҄҅҆҇҈҉ҊҋҌҍҎҏҐґҒғҔҕҖҗҘҙҚқҜҝҞҟҠҡҢңҤҥҦҧҨҩҪҫҬҭҮүҰұ'
                    'ҲҳҴҵҶҷҸҹҺһҼҽҾҿӀӁӂӃӄӅӆӇӈӉӊӋӌӍӎӏӐӑӒӓӔӕӖӗӘәӚӛӜӝӞӟӠӡӢӣӤӥӦӧӨө'
                    'ӪӫӬӭӮӯӰӱӲӳӴӵӶӷӸӹӺӻӼӽӾӿ' for x in text0):
            if not SILENT:
                print('{}: non-Russian'.format(link_no))
            text = None
            break
        if text0 and len(text1) / len(text0) >= .9:
            num_words = len([x for x in text.split()
                               if re5.sub('', x)])
            #print(num_words)
            if num_words > MAX_CHUNK_WORDS:
                lines = lines[:-1]
                continue
            if num_words >= MIN_CHUNK_WORDS:
                res = True
        else:
            if not SILENT:
                print('{}: non-Cyrillic'.format(link_no))
            text = None
        break
    if not res:
        if not SILENT:
            if not text:
                print('no text')
                #if nop:
                #    exit()
            else:
                print('text beyond limits:')
                print(text)
        continue
    texts_total += 1
    if link_no > start_link_idx:
        with open(page_fn, 'wt', encoding='utf-8') as f:
            print(link, file=f)
            f.write(page)
    with open(text_fn, 'wt', encoding='utf-8') as f:
        print(link, file=f)
        f.write(text)
    print('\r{} (of {})'.format(texts_total, utils.TEXTS_FOR_SOURCE), end='')
    need_enter = True
    #exit()
if need_enter:
    print()
exit()
'''===========================================================================
Chunks creation
==========================================================================='''
_utils.make_chunks(num_links)

'''===========================================================================
Tokenization
==========================================================================='''
utils.tokenize(num_links, isdialog=False)
