#!/bin/sh

find . -type d -exec touch {}/.stats_cache ';'
find . -type f \( -name *.ann -o -name .stats_cache \) -exec chmod 666 {} ';'
#find . -type d -exec chmod 777 {} ';'
