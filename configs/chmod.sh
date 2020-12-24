#!/bin/sh

find . -type f \( -name *.txt -o -name *.ann \) -exec chmod 666 {} ';'
find . -type d -exec chmod 777 {} ';'
