#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from collections import OrderedDict
import os
import random
import re

###
import sys
sys.path.append('../')
###
import utils


SEED = 42
ROOT_URL = 'https://theatre-library.ru'
INIT_URL = ROOT_URL + '/works/?page={}'
MIN_TEXT_LINES = 4
MAX_TEXT_LINES = 20
MIN_CHUNK_WORDS = 40
MAX_CHUNK_WORDS = 200
SKIP_FIRST = 100
SILENT = False

if SEED:
    random.seed(SEED)

links = []

'''===========================================================================
Authors download
==========================================================================='''
if os.path.isfile(utils.LINKS_FN):
    with open(utils.LINKS_FN, 'rt', encoding='utf-8') as f:
        links = [x for x in f.read().split('\n')
                   if x and not x.startswith('#')]

else:
    links = OrderedDict()
    res = utils.get_url(INIT_URL.format(1))
    res = res.text
    token = '<li class="pager-last last"><a href="/works/?page='
    pos = res.find(token)
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    res = res[pos + len(token):]
    pos = res.find('"')
    assert pos >= 0, "ERROR: Can't find authors on {}".format(url)
    max_page_no = int(res[:pos])
    for page_no in range(1, max_page_no + 1):
        url = INIT_URL.format(page_no)
        res = utils.get_url(url)
        res = res.text
        res = res.split(
            "<div class='dw_ch'><div class='dw_ch_ch'><div class='th_d1'>"
        )[1:]
        if page_no != max_page_no and len(res) != 100:
            print('\nWARNING: Only {} books on {}'.format(len(res), url))
        for book in res:
            token = "<a class='uline' href=\""
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('"')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book_url = book[:pos]
            book = book[pos:]
            token = "<a class='uline' href='/authors/"
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find("'>")
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            author_url = '/authors/' + book[:pos]
            book = book[pos + 2:]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            author_name = utils.norm_text2(book[:pos]).strip()
            book = book[pos:]
            token = '<div class="desc2">'
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            genre = book[:pos]
            book = book[pos:]
            #pos = genre.find(',')
            #if pos > 0:
            #    genre = genre[:pos]
            token = "<div class='desc2'>Язык оригинала: "
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book_ = book[:pos]
            pos = book_.find(';')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            lang = book_[:pos]
            book_ = book_[pos:]
            token = '; период написания: '
            pos = book_.find(token)
            if pos >= 0:
                book_ = book_[pos + len(token):]
                pos = book_.find(' век')
                if pos < 0:
                    pos = book_.find(',')
                centure = book_[:pos] if pos > 0 else book_
            else:
                centure = '<UNK>'
            token = "<div class='desc2'>Формат файла: "
            pos = book.find(token)
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book = book[pos + len(token):]
            pos = book.find('<')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            book_ = book[:pos]
            pos = book_.find(';')
            assert pos >= 0, \
                'ERROR: Not found: {}\n{}\n{}'.format(url, token, book)
            format = book_[:pos]
            links[book_url] = (lang, genre, centure, format, author_url, author_name)
        print('\r{} (of {})'.format(page_no, max_page_no), end='')
    links = list('\t'.join([x, '\t'.join(y)]) for x, y in links.items())

    random.shuffle(links)
    with open(utils.LINKS_FN, 'wt', encoding='utf-8') as f:
        f.write('\n'.join(links))
    print()

links_, links, author_links = links, [], OrderedDict()
langs, genres, centures, formats = {}, {}, {}, {}
for link in links_:
    book_url, lang, genre, centure, format, author_url, author_name = \
        link.split('\t')
    if lang == 'русский' and centure in ['XXI', 'XX', '<UNK>'] \
                         and genre not in [
        'Аннотация, синопсис',
        'Биография, автобиография',
        'Воспоминания, мемуары',
        'Критика, отзывы, интервью',
        'Публикации, статьи, заметки',
        'Сборник произведений',
        'Теоретическая работа, монография',
        'Учебник, учебное пособие'
    ]:
        links.append(book_url)
        if author_url in author_links:
            author_links[author_url].append((book_url, format))
        else:
            author_links[author_url] = [(book_url, format)]
'''
    langs[lang] = langs.get(lang, 0) + 1
    genres[genre] = genres.get(genre, 0) + 1
    centures[centure] = centures.get(centure, 0) + 1
    formats[format] = formats.get(format, 0) + 1
with open('langs', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(langs.items())))
with open('genres', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(genres.items())))
with open('centures', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(centures.items())))
with open('formats', 'wt', encoding='utf-8') as f:
    f.write('\n'.join('\t'.join([x, str(y)]) for x, y in sorted(formats.items())))
'''
num_links = len(links)

'''===========================================================================
Files download
==========================================================================='''
'''for link_no, link in enumerate(links, start=1):
    pos = link.rfind('/')
    page_fn = os.path.join(utils.PAGES_DIR, link[pos + 1:])
    if not os.path.isfile(page_fn):
        page = utils.get_url(ROOT_URL + link)
        with open(page_fn, 'wb') as f:
            f.write(page.content)
    print('\r{} (of {})'.format(link_no, num_links), end='')
print()
'''
'''===========================================================================
Texts collection
==========================================================================='''
text_fns = utils.get_file_list(utils.TEXTS_DIR, utils.TEXTS_FOR_SOURCE)
if text_fns:
    print('INFO: The texts directory is not empty. The stage skipped')
else:
    FMT_DELIM = '|'
    NODLG_FIRST = 3
    RU_UP, RU_LO = 'ЁА-Я', 'ёа-я'
    RU_ALL = RU_UP, RU_LO
    INT_UP, INT_LO = RU_UP + 'A-Z', RU_LO + 'a-z'
    INT_ALL = INT_UP + INT_LO
    INT_ALL_LETTERS = 'Ё' \
                   + ''.join(chr(x) for x in list(range(ord('А'), ord('Я') + 1))) \
                   + 'ё' \
                   + ''.join(chr(x) for x in list(range(ord('а'), ord('я') + 1))) \
                   + ''.join(chr(x) for x in list(range(ord('A'), ord('Z') + 1))) \
                   + ''.join(chr(x) for x in list(range(ord('a'), ord('z') + 1)))
    re0 = re.compile(r'\W|\d')
    re1 = re.compile(r'[^{}]'.format(RU_ALL))
    re5 = re.compile(r'\W')
    #re8 = re.compile(r'(\S) {1,3}(\S)')
    re10 = re.compile(r'(?:\(.*?\)|/.*?/|\[.*?])')
    sent_tpl_up = r'(\W?? *[{0}](?:[^{1}].*)?\W$)'.format(INT_UP, INT_UP)
    sent_tpl_lo = r'(\W?? *[{0}](?:[^{1}].*)?\W$)'.format(INT_LO, INT_UP)
    sent_tpl_all = r'(\W?? *[{0}]?(?:[^{1}й].*)??\W$)'.format(INT_UP, INT_UP)
    rex0 = [
        # АЛЕКСАНДР СЕРГЕЕВИЧ. Ааа ааа аааа...
        # СЕМЁН-АЛЕКСАНДР:Ааа ааа аааа...
        # РОБОТ, БАРАН Ааа ааа аааа...
        re.compile(r'(["«<]?(?:\d+-(?:й|я|ый|ая|ий|вый|тий) )?[\d{0}]+(?:(?:-| {{1,2}}|[.,] | и ?)[\d{0}]+){{,6}}["»>]?)([.:] ?| -|- | +){3}'
                        .format(INT_UP, INT_LO, INT_ALL, sent_tpl_up)),
        re.compile(r'(["«<]?(?:\d+-(?:й|я|ый|ая|ий|вый|тий) )?[\d{0}]{{2,}}(?:(?:-| |[.,] | и ?)[\d{0}]{{2,}}){{,6}}["»>]?)([.:] ?| -|- | +){3}'
                        .format(INT_UP, INT_LO, INT_ALL, sent_tpl_lo)),
        # Петя к Марии. Ааа ааа аааа...
        re.compile(r'([\d{0}][\d{1}]*(?:(?:[ -]| к )[\d{0}][\d{1}]*){{,2}})([.:] ?| -|- |  ){3}'
                        .format(INT_UP, INT_LO, INT_ALL, sent_tpl_all)),
        # Первый актер. Ааа ааа аааа...
        re.compile(r'(["«<]?[\d{0}]-?[\d{1}]*(?:[ -][\d{1}]+){{,2}}["»>]?)([.:] ?| -|- |  ){3}'
                        .format(INT_UP, INT_LO, INT_ALL, sent_tpl_all)),
        # 1-й М а к - К и н л и: Ааа ааа аааа...
        re.compile(r'((?:\d+-(?:й|я|ый|ая|ий|вый|тий) )?[\d{0}]:?(?:[ _][\d{1}-])*(?: {{1,3}}[\d{0}](?:[ _][\d{1}-])*)*)([.:] ?| -|- |  ){3}'
                        .format(INT_UP, INT_LO, INT_ALL, sent_tpl_all)),
        # Петя Иванов. ааа ааа аааа...
        re.compile(r'([\d{0}][\d{0}]*(?:[ -][\d{1}][\d{2}]*){{,2}})([.:]| -|- |  ){3}'
                        .format(INT_ALL, INT_UP, INT_LO, sent_tpl_all)),
        re.compile(r'(-)( ?)(.+?$)') 
    ]

    def check_text(lines):
        res = False
        text = '\n'.join(x[1] for x in lines)
        text0 = re0.sub('', text)
        text1 = re1.sub('', text0)
        if any(x in 'ЀЂЃЄЅІЇЈЉЊЋЌЍЎЏѐђѓєѕіїјљњћќѝўџѠѡѢѣѤѥѦѧѨѩѪѫѬѭѮѯѰѱѲѳѴѵѶѷѸѹ'
                    'ѺѻѼѽѾѿҀҁ҂҃҄҅҆҇҈҉ҊҋҌҍҎҏҐґҒғҔҕҖҗҘҙҚқҜҝҞҟҠҡҢңҤҥҦҧҨҩҪҫҬҭҮүҰұ'
                    'ҲҳҴҵҶҷҸҹҺһҼҽҾҿӀӁӂӃӄӅӆӇӈӉӊӋӌӍӎӏӐӑӒӓӔӕӖӗӘәӚӛӜӝӞӟӠӡӢӣӤӥӦӧӨө'
                    'ӪӫӬӭӮӯӰӱӲӳӴӵӶӷӸӹӺӻӼӽӾӿ' for x in text0):
            if not SILENT:
                print(text)
                print('non-Russian')
        elif text0 and len(text1) / len(text0) >= .9:
            num_words = len([x for x in text.split()
                               if re5.sub('', x)])
            #print(num_words)
            if num_words > MAX_CHUNK_WORDS:
                res = 1
            if num_words >= MIN_CHUNK_WORDS:
                res = True
            else:
                res = -1
        else:
            if not SILENT:
                print(text)
                print(text0)
                print(text1)
                print(len(text1) / len(text0))
                print('non-Cyrillic')
        return res

    num_links = len(author_links)
    texts_total, need_enter = 0, False
    for link_no, (author_url, book_infos) in enumerate(author_links.items(),
                                                       start=1):
        #if texts_total >= utils.TEXTS_FOR_SOURCE:
        #    break
        text_fn = utils.get_data_path(utils.TEXTS_DIR,
                                      utils.TEXTS_FOR_SOURCE, link_no)
        for book_url, book_format in book_infos:
            text = None
            pos = book_url.rfind('/')
            page_fn = os.path.join(utils.PAGES_DIR, book_url[pos + 1:])
            #TODO:
            #page_fn_ = page_fn.replace(utils.PAGES_DIR, os.path.join(utils.TEXTS_DIR, '0'))
            #if os.path.isfile(page_fn_):
            #    texts_total += 1
            #    print('\r{}\r{}'.format(' ' * 60, texts_total), end='')
            #    continue
            #####
            if not os.path.isfile(page_fn):
                continue
            if not SILENT:
                print(book_url[pos + 1:])
            if book_format in ['doc', 'docx', 'rtf']:
                text = utils.convert_doc(page_fn)
                #text = utils.convert_odt(page_fn)
            elif book_format == 'html':
                text = utils.convert_html(page_fn)
            elif book_format == 'pdf':
                #pdftotext -enc UTF-8 [-layout] [-raw] [-simple] [-simple2] -nopgbrk page_fn text_fn
                #pdftohtml -nofonts -skipinvisible page_fn <output_dir>
                text = utils.convert_pdf(page_fn)
            elif book_format == 'txt':
                with open(page_fn, 'rt', encoding='utf=8') as f:
                    text = f.read()
            DUMP = False
            if DUMP:
                with open('1111', 'wt', encoding='utf-8') as f:
                    f.write(text)
            #TODO:
            #if text:
            #    with open(page_fn_, 'wt', encoding='utf-8') as f:
            #        print(ROOT_URL + book_url, file=f)
            #        f.write(text)
            #texts_total += 1
            #print('\r{}\r{}'.format(' ' * 60, texts_total), end='')
            #continue
            #####
            # убираем текст в скобках, сжимаем пробелы, разбиваем на строки
            # и оставляем только непустые
            text = utils.norm_text2(text)
            # workarounds:
            koi_chars = '▀└┘▒▓⌠■√≈⌡═╗╘╚╦╧╩' + '╬'
            win_chars = '‹„…‘’“”–—› Ё©«ё№»' + '…'
            for koi_, win_ in zip(koi_chars, win_chars):
                text = text.replace(koi_, win_)
            text = text.replace('–', '-').replace('—', '-') \
                       .replace('―', '-').replace('--', '-') \
                       .replace('. -', '.').replace(': -', ':')
            text = re.sub(r'²(.*?)›', r'“\g<1>”', text)
            ###
            if text:
                lines, is_opened, is_table_opened = [], False, False
                for line in text.split('\n'):
                    line = re.sub(r'(^|[^!?] *)\. *\. *([^!?]|$)',
                                  r'\g<1>… \g<2>',
                           re.sub(r'(?:[.,] *){3,}', r'… ', line)) \
                             .replace('\t', ' ' * 4).strip()
                    line_ = re.sub(r'^\|([^|]+)\|([^|]+)\|$',
                                   r'\g<1>    \g<2>', line)
                    if line_ != line:
                        line = line_.strip()
                        if not line_.startswith(' '):
                            is_table_opened = True
                        elif lines:
                            if not line_:
                                is_table_opened = False
                            if is_table_opened:
                                is_opened = True
                    line = re.sub(r'^\|(.*)\|$', r'\g<1>', line).strip()
                    #print(is_opened)
                    #print(line)
                    if line:
                        if is_opened and ' ' * 3 not in line:
                            lines[-1] += (' ' * 3) + line
                        else:
                            lines.append(line)
                        if line[-1] in INT_ALL_LETTERS + '0123456789,:;-':
                            is_opened = True
                            continue
                    is_opened = False
                # workaround
                lines = [x for x in (
                    re.sub(r'…\.+', '…',
                    re.sub(r'^[№•]\s*', '', re.sub(r'^\?{2,}\s*', '',
                    re.sub(r'^([{0}])\.([{1}])'
                               .format(INT_UP, INT_LO),
                           r'\g<1>\g<2>',
                    re.sub(r'^(\w{1,3})\. ?(\d:)', r'\g<1>\g<2>',
                    re.sub(r'^([{0}])\. ?([{1}]\.)'
                               .format(INT_UP, INT_ALL),
                           r'\g<1>\g<2>',
                    re.sub(r'^([{0}])\. ?([{0}])(\. ?([{0}]))?'
                               .format(INT_UP),
                           r'\g<1>\g<2>\g<3>',
                    re.sub(r' +([.:])', r'\g<1>',
                    re.sub(r'([.?!-]) +[.:]', r'\g<1>',
                    re10.sub('', x)))))))))).strip()
                        for x in lines
                ) if x]
                ###
                if DUMP:
                    with open('2222', 'wt', encoding='utf-8') as f:
                        f.write('\n'.join(lines))
                # ищем подходящий формат файла
                TRACE0 = False
                speaker_fmts = {}
                for line in lines:
                    if TRACE0:
                        print(line)
                    for rex_no, rex, in enumerate(rex0):
                        match = rex.match(line)
                        if match:
                            if TRACE0:
                                print(match)
                            speaker, fmt_ending, _ = match.groups()
                            fmt_ending = fmt_ending.strip()
                            speaker_fmt = str(rex_no) + FMT_DELIM + fmt_ending
                            speaker_fmts[speaker_fmt] = \
                                speaker_fmts.get(speaker_fmt, 0) + 1
                TRACE1 = False
                if TRACE0 or TRACE1:
                    print(speaker_fmts)
                if all(x < (MIN_TEXT_LINES + MAX_TEXT_LINES) // 2
                           for x in speaker_fmts.values()):
                    # book doesn't have proper formatting
                    if not SILENT:
                        print('WARINIG: Format is unknown '
                              '(or text is too short)')
                    continue
                speaker_fmt, speaker_fmt_ending = \
                    max(speaker_fmts.items(),
                        key=lambda x: x[1])[0].split(FMT_DELIM)
                REX = rex0[int(speaker_fmt)]
                if TRACE1 == True:
                    print(REX)
                # ищем всех спикеров
                speakers = {}
                for line in lines:
                    match = REX.match(line)
                    if match:
                        speaker = match.group(1)
                        speakers[speaker] = speakers.get(speaker, 0) + 1
                # ищем диалоги. между ними м.б. несколько ремарок, но
                # не особо много
                all_dlg_lines = []
                nodlg, dlg_lines = 0, []
                for line in lines:#[start_line_no:]:
                    if TRACE1 == True:
                        print(line)
                    if re.match(r'[\d{},;:-]'.format(INT_ALL), line[-1]):
                        if len(dlg_lines) >= MIN_TEXT_LINES:
                            all_dlg_lines.append(dlg_lines)
                        if TRACE1 == True:
                            print('ENDING')
                        nodlg, dlg_lines = 0, []
                        continue
                    match = REX.match(line)
                    if match:
                        speaker, fmt_ending, sentence = match.groups()
                        fmt_ending = fmt_ending.strip()
                        if speakers.get(speaker, 0) < 6:
                            if TRACE1 == True:
                                print('RARE')
                            if len(dlg_lines) >= MIN_TEXT_LINES:
                                all_dlg_lines.append(dlg_lines)
                            nodlg, dlg_lines = 0, []
                            continue
                        if fmt_ending == speaker_fmt_ending:# or not fmt_ending:
                            if nodlg >= NODLG_FIRST:
                                if TRACE1 == True:
                                    print('NODLG')
                                if len(dlg_lines) >= MIN_TEXT_LINES:
                                    all_dlg_lines.append(dlg_lines)
                                nodlg, dlg_lines = 0, []
                            if TRACE1 == True:
                                print('OK')
                            if not sentence.startswith('..'):
                                sentence = re.sub(r'^\s*[-:.,;]?\s*', '',
                                           re.sub(r'\s+', ' ', sentence))
                            dlg_lines.append((speaker, sentence))
                        else:
                            if TRACE1 == True:
                                print('ENDING: {} vs {}'
                                          .format(fmt_ending,
                                                  speaker_fmt_ending))
                            nodlg += 1
                            # cheat mode on
                            if len(dlg_lines) >= MIN_TEXT_LINES:
                                all_dlg_lines.append(dlg_lines)
                            nodlg, dlg_lines = 0, []
                    else:
                        if TRACE1 == True:
                            print('NO MATCH')
                        nodlg += 1
                        # cheat mode on
                        if len(dlg_lines) >= MIN_TEXT_LINES:
                            all_dlg_lines.append(dlg_lines)
                        nodlg, dlg_lines = 0, []
                if len(dlg_lines) >= MIN_TEXT_LINES:
                    all_dlg_lines.append(dlg_lines)
                #print(all_dlg_lines)
                if not all_dlg_lines:
                    if not SILENT:
                        print("WARINIG: Can't collect a fragment")
                    continue
                check_result = None
                for dlg_lines_ in sorted(all_dlg_lines, key=lambda x: len(x),
                                         reverse=True):
                    for start_idx in range(max(1, len(dlg_lines_)
                                                - MAX_TEXT_LINES)):
                        dlg_lines = \
                            dlg_lines_[start_idx:start_idx + MAX_TEXT_LINES]
                        #print(dlg_lines)
                        while True:
                            check_result = check_text(dlg_lines)
                            # Note: isinstance(True, int) == True
                            if not isinstance(check_result, bool):
                                if check_result < 0:
                                    check_result = False
                                elif check_result > 0:
                                    dlg_lines = dlg_lines[:-1]
                                    continue
                            break
                        # too lazy to defne an exception
                        if check_result:
                            break
                    if check_result:
                        break
                if not check_result:
                    if not SILENT:
                        print('WARINIG: Fragment is too short')
                    continue
                texts_total += 1
                text = '\n'.join('\t'.join(x) for x in dlg_lines)
                with open(text_fn, 'wt', encoding='utf-8') as f:
                    print(ROOT_URL + book_url, file=f)
                    f.write(text)
                #TODO:!!!
                #os.remove(page_fn)
                #page_fn_ = page_fn.replace(utils.PAGES_DIR, os.path.join(utils.TEXTS_DIR, '0'))
                #if os.path.isfile(page_fn_):
                #    os.remove(page_fn_)
                #####
            print('\r{}\r{} (of {})'
                      .format(' ' * 60, texts_total,
                              min(utils.TEXTS_FOR_SOURCE, num_links)),
                  end='')
            need_enter = True
            break
    if need_enter:
        print('\r{}\r{} (of {})'
                  .format(' ' * 60, texts_total,
                          min(utils.TEXTS_FOR_SOURCE,
                              num_links + texts_total - link_no)))

'''===========================================================================
Chunks creation
==========================================================================='''
chunk_fns = utils.get_file_list(utils.CHUNKS_DIR, utils.TEXTS_FOR_SOURCE)
if chunk_fns:
    print('INFO: The chunks directory is not empty. The stage skipped')
else:
    text_fns = utils.get_file_list(utils.TEXTS_DIR, utils.TEXTS_FOR_SOURCE)
    text_idx = 0
    for text_idx, text_fn in enumerate(text_fns[:utils.CHUNKS_FOR_SOURCE],
                                       start=1):
        chunk_fn = text_fn.replace(utils.TEXTS_DIR, utils.CHUNKS_DIR)
        assert chunk_fn != text_fn, 'ERROR: invalid path to text file'
        with open(text_fn, 'rt', encoding='utf-8') as f_in, \
             open(chunk_fn, 'wt', encoding='utf-8') as f_out:
            f_in.readline()
            f_out.write(f_in.read())
            print('\r{} (of {})'.format(text_idx, utils.CHUNKS_FOR_SOURCE),
                  end='')
    if text_idx:
        print()

'''===========================================================================
Tokenization
==========================================================================='''
conll_fns = utils.get_file_list(utils.CONLL_DIR, utils.TEXTS_FOR_SOURCE)
if not conll_fns:
    utils.tokenize(utils.TEXTS_FOR_SOURCE, isdialog=True)
elif len(conll_fns) < utils.CONLL_FOR_SOURCE:
    print('The conll directory is not empty but not full. '
          'Delete all .txt files from there to recreate conll')
    exit()
