#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from toxine import brat


brat.renew_ann_dir(r'C:\prj-git\_mine\ru_corner\_data\brat\tagged',
                   r'C:\prj-git\_mine\ru_corner\_data\brat\final',
                   recursive=True, rewrite=True, ignore_absent=False)
'''
fn = r'dashleo\newswire\lenta.ru\0028'
brat.renew_ann(r'C:\prj-git\_mine\ru_corner\_data\brat\tagged\{}.txt'.format(fn),
               r'C:\prj-git\_mine\ru_corner\_data\brat\tagged\{}.ann'.format(fn),
               r'C:\prj-git\_mine\ru_corner\_data\brat\final\{}.txt'.format(fn),
               r'C:\prj-git\_mine\ru_corner\_data\brat\final\{}.ann'.format(fn),
               rewrite=True)
'''
