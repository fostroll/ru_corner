#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from toxine import brat


brat.renew_ann_dir(r'C:\prj-git\_mine\ru_corner\_ner.old2',
                   r'C:\prj-git\_mine\ru_corner\_data\brat\assignments\pass1',
                   recursive=True, rewrite=True, ignore_absent=True)
'''
brat.renew_ann(r'C:\prj-git\_mine\ru_corner\_ner.old\dashleo\newswire\russian.rt.com\0065.txt',
               r'C:\prj-git\_mine\ru_corner\_ner.old\dashleo\newswire\russian.rt.com\0065.ann',
               r'C:\prj-git\_mine\ru_corner\_data\brat\assignments\pass1\dashleo\newswire\russian.rt.com\0065.txt',
               r'C:\prj-git\_mine\ru_corner\_data\brat\assignments\pass1\dashleo\newswire\russian.rt.com\0065.ann')
'''
