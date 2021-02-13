#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

import sys
from toxine import brat


assert len(sys.argv) == 3, \
    'ERROR: Syntax is: {} <domain> <source>'.format(sys.argv[0])
domain, source = sys.argv[1:]

brat.renew_ann_dir(r'C:\prj-git\_mine\ru_corner\_data\brat\tagged\{}\{}'.format(domain, source),
                   r'C:\prj-git\_mine\ru_corner\_data\brat\final\{}\{}'.format(domain, source),
                   recursive=True, rewrite=True, ignore_absent=False)
'''
fn = r'dashleo\newswire\lenta.ru\0028'
brat.renew_ann(r'C:\prj-git\_mine\ru_corner\_data\brat\tagged\{}.txt'.format(fn),
               r'C:\prj-git\_mine\ru_corner\_data\brat\tagged\{}.ann'.format(fn),
               r'C:\prj-git\_mine\ru_corner\_data\brat\final\{}.txt'.format(fn),
               r'C:\prj-git\_mine\ru_corner\_data\brat\final\{}.ann'.format(fn),
               rewrite=True)
'''
