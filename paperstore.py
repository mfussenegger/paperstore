#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import hashlib

from subprocess import Popen, call
from config import DEVICE, DEFAULT_LANGUAGE

import whoosh.index as index
from whoosh.fields import Schema, TEXT, STORED, KEYWORD, ID
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser


index_path = os.path.join(os.path.dirname(__file__), 'index')
schema = Schema(content=TEXT(stored=True),
                hashvalue=ID,
                tags=KEYWORD,
                time=STORED,
                blob=STORED)


def scan(tags=None):
    do_scan()
    create_tiff_and_txt()
    merge_tiff_and_txt()


def merge_tiff_and_txt():
    with open('content.txt', 'w') as fout:
        for f in os.listdir(os.curdir):
            if f.startswith('_out') and f.endswith('.txt'):
                with open(f, 'r') as fin:
                    fout.write(fin.read())
                os.remove(f)

    call(['tiffcp', '-c', 'lzw', '*.tiff', 'content.tiff'])
    call('tiff2pdf content.tiff > content.pdf', shell=True)
    os.rename('_out1.tiff', 'preview.tiff')
    for f in os.listdir(os.curdir):
        if f.startswith('_out') and f.endswith('.tiff'):
            os.remove(f)


def create_tiff_and_txt():
    pnms = [f for f in os.listdir(os.curdir) if f.endswith('.pnm')]
    print(pnms)
    for pnm in sorted(pnms):
        unpapered = '_' + pnm
        call(['unpaper', pnm, unpapered])
        if os.path.exists(unpapered):
            os.remove(pnm)

        tiff = unpapered.replace('.pnm', '.tiff')
        call(['convert', unpapered, tiff])
        if os.path.exists(tiff):
            os.remove(unpapered)
            call(['tesseract',
                  tiff,
                  tiff.replace('.tiff', ''),
                  '-l',
                  DEFAULT_LANGUAGE])


def do_scan():
    p = Popen(['scanimage',
               '--device',
               DEVICE,
               '--format=pnm',
               '--resolution',
               '300',
               '-x',
               '210',
               '-y',
               '297',
               '--batch',
               '--source',
               'ADF'])
    p.wait()


def add(path_text, path_blob, tags=None):
    with open(path_text, 'r') as fi_txt:
        content = fi_txt.read().decode('utf-8')

    with open(path_blob, 'rb') as fi_blb:
        blob = fi_blb.read()
        hashvalue = hashlib.sha1(blob).hexdigest()
        modtime = os.path.getmtime(path_blob)

    ix = open_dir(index_path)
    writer = ix.writer()
    writer.add_document(content=content,
                        tags=tags,
                        blob=blob,
                        time=modtime,
                        hashvalue=unicode(hashvalue))
    writer.commit()


def search(term):
    ix = open_dir(index_path)
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        query = parser.parse(term)
        results = searcher.search(query)
        for result in results:
            print('{0}:' .format(result['hashvalue']))


def openfile(hashvalue):
    if os.name == 'nt':
        pass
    elif os.name == 'mac':
        # open
        pass
    elif os.name == 'posix':
        # xdg-open, gnome-open
        pass


def create():
    if not os.path.exists(index_path):
        os.mkdir(index_path)

    if not index.exists_in(index_path):
        create_in(index_path, schema)


def main():
    pass

if __name__ == '__main__':
    main()
