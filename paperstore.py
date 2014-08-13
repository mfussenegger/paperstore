#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import webbrowser
import argh

from sh import (
    scanimage,
    convert,
    unpaper,
    tesseract,
    tiffcp
)

from time import time
from uuid import uuid4

from bottle import route, run, post, request, static_file
from bottle import jinja2_template as template

from config import DEVICE, DEFAULT_LANGUAGE, CRATE_HOSTS
from crate.client import connect


connection = connect(CRATE_HOSTS)
cursor = connection.cursor()
blobs = connection.get_blob_container('docs')

INSERT_STMT = '''\
insert into docs (id, content, tags, preview_hash, pdf_hash, ts)
    values (?, ?, ?, ?, ?, ?)
'''

def mktime():
    return int(time() * 1000)


@argh.arg('--tags', nargs='+')
def scan(tags=None, lang=None):
    pnms = do_scan()
    tiffs, textfiles = create_tiff_and_txt(pnms, lang)
    fp, content = merge_textfiles(textfiles)
    tiff = merge_tiffs(tiffs)
    pdf = tiff_to_pdf(tiff)

    pdf_hash = blobs.put(open(pdf, 'rb'))
    preview_hash = blobs.put(open('preview.jpg', 'rb'))
    cursor.execute(INSERT_STMT, (
        str(uuid4()), content, tags, preview_hash, pdf_hash, mktime()))


def merge_textfiles(textfiles):
    content = []
    with open('content.txt', 'w') as fout:
        for f in textfiles:
            with open(f, 'r') as fin:
                tmp = fin.read()
                content.append(tmp)
                fout.write(tmp)
            os.remove(f)
    return 'content.txt', '\n'.join(content)


def merge_tiffs(tiffs):
    tiffs = tiffs or [f for f in os.listdir(os.curdir)
                      if f.startswith('_out') and f.endswith('.tiff')]
    if not tiffs:
        sys.exit('No tiff files found')
    tiffcp(tiffs, 'content.tiff')
    convert(tiffs[0], 'preview.jpg')
    for tiff in tiffs[1:]:
        os.remove(tiff)
    return 'content.tiff'


def tiff_to_pdf(tiff):
    convert(
        '-compress', 'JPEG',
        '-page', 'A4',
        tiff,
        'content.pdf'
    )
    os.remove('content.tiff')
    return 'content.pdf'


def create_tiff_and_txt(pnms, language):
    language = language or DEFAULT_LANGUAGE
    tiffs = []
    texts = []
    for pnm in sorted(pnms):
        unpapered = '_' + pnm
        unpaper(pnm, unpapered)
        if os.path.exists(unpapered):
            os.remove(pnm)

        tiff = unpapered.replace('.pnm', '.tiff')
        convert(unpapered, tiff)
        if os.path.exists(tiff):
            os.remove(unpapered)
            txtfile = tiff.replace('.tiff', '')
            tiffs.append(tiff)
            texts.append(txtfile + '.txt')
            tesseract(tiff, txtfile, '-l', language)
    return tiffs, texts


def do_scan():
    scanimage(
        '--device',
        DEVICE,
        '--format=pnm',
        '--resolution', 300,
        '-x', 210,
        '-y', 297,
        '--batch',
        '--source', 'ADF',
        _ok_code=[0, 7]
    )
    pnms = [f for f in os.listdir(os.curdir) if f.endswith('.pnm')]
    return pnms


@route('/')
def search():
    return template('index', term='')


@post('/')
def search_submit():
    term = request.forms.get('term')
    if not term:
        return template('index', term='')

    stmt = 'select content, preview_hash, pdf_hash, tags, ts from docs \
        where match (content, ?) limit 20'
    cursor.execute(stmt, (term, ))
    rows = cursor.fetchall()
    rows = [{
        'tags': r[3],
        'date': r[4],
        'preview': r[1],
        'pdf': r[2],
        'content': r[0]} for r in rows]
    return template('index', results=rows, term=term)


@route('/preview/<year>/<month>/<filename>')
def preview(year, month, filename):
    return static_file('{0}/{1}/{2}'.format(year, month, filename),
                       'archive/',
                       'image/tiff')


def runserver():
    webbrowser.open_new_tab('http://localhost:8080/')
    run(host='localhost', port=8080, reloader=True)


def main():
    parser = argh.ArghParser()
    parser.add_commands([scan, runserver])
    parser.dispatch()


if __name__ == '__main__':
    main()
