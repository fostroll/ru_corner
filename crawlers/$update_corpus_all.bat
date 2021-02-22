find ../corpus/ner/brat -name .stats_cache -exec rm {} ';'
call update_corpus newswire lenta.ru
call update_corpus newswire russian.rt.com
call update_corpus newswire www.gazeta.ru
call update_corpus newswire www.kp.ru
