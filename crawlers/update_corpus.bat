find ../corpus/ner/brat -name .stats_cache -exec rm {} ';'
python brat_to_conll.py %1 %2
python conll_merge.py %1 %2
