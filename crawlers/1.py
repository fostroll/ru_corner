#!/usr/bin/python -u
#-*- encoding: utf-8 -*-

from toxine import brat

fn = '0005.txt'
out_fn = '0005.conllu'
#brat.brat_to_conllu(fn, save_to=out_fn, keep_tokens='smart')
brat.brat_to_conllu(fn, save_to=out_fn, keep_tokens=True)
