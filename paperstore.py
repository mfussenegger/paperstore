#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import hashlib
import webbrowser
from argh import command, ArghParser

from datetime import datetime

from bottle import route, run, post, request, static_file
from bottle import jinja2_template as template

from subprocess import Popen, call
from config import DEVICE, DEFAULT_LANGUAGE

import whoosh.index as index
from whoosh.fields import Schema, TEXT, ID, KEYWORD, DATETIME
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser


path_archive = os.path.join(os.path.dirname(__file__), 'archive')
path_index = os.path.join(path_archive, 'index')
schema = Schema(content=TEXT,
               tags=KEYWORD(stored=True,
                            lowercase=True,
                            commas=True,
                            scorable=True),
               path=ID(stored=True),
               date=DATETIME(stored=True))


@command
def scan(tags=None):
    do_scan()
    create_tiff_and_txt()
    merge_tiff_and_txt()

    tags = unicode(tags, encoding='utf-8', errors='ignore'),
    add('content.txt', 'content.pdf', 'preview.tiff', tags)


def merge_tiff_and_txt():
    with open('content.txt', 'w') as fout:
        for f in os.listdir(os.curdir):
            if f.startswith('_out') and f.endswith('.txt'):
                with open(f, 'r') as fin:
                    fout.write(fin.read())
                os.remove(f)

    call('tiffcp -c lzw *.tiff content.tiff', shell=True)
    call('tiff2pdf content.tiff > content.pdf', shell=True)
    os.rename('_out1.tiff', 'preview.tiff')
    for f in os.listdir(os.curdir):
        if f.startswith('_out') and f.endswith('.tiff'):
            os.remove(f)
    os.remove('content.tiff')


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


def add(path_text, path_pdf, path_preview, tags=None):
    with open(path_text, 'r') as ftxt:
        content = ftxt.read().decode('utf-8')

    with open(path_pdf, 'rb') as fpdf:
        pdf = fpdf.read()
        hashvalue = hashlib.sha1(pdf).hexdigest()

    dt = datetime.now()
    dir = os.path.join(path_archive, '{0:%Y/%m}/'.format(dt))
    pdf = os.path.abspath(os.path.join(path_archive,
                        '{0:%Y/%m}/{1}.pdf'.format(dt, hashvalue)))
    preview = os.path.abspath(os.path.join(path_archive,
                        '{0:%Y/%m}/{1}_preview.png'.format(dt,
                                                            hashvalue)))

    ix = open_dir(path_index)
    writer = ix.writer()
    writer.add_document(content=content,
                        tags=tags,
                        path=unicode(pdf),
                        date=dt)
    writer.commit()

    if not os.path.exists(dir):
        os.makedirs(dir)
    os.rename(path_pdf, pdf)
    call(['convert', '-resize', '200x', path_preview, preview])
    os.remove(path_preview)
    os.remove(path_text)


@route('/')
def search():
    return template('index', term='')


@post('/')
def search_submit():
    term = request.forms.get('term')
    if not term:
        return template('index', term='')

    ix = open_dir(path_index)
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema)
        query = parser.parse(unicode(term))
        results = searcher.search(query)
        results = [{
            'tags': r.get('tags'),
            'date': r['date'],
            'path': r['path'],
            'preview': '/preview/{0:%Y/%m}/{1}_preview.png'.format(
                r['date'],
                os.path.basename(r['path']).replace('.pdf', ''))
        } for r in results]
    return template('index', results=results, term=term)


@route('/preview/<year>/<month>/<filename>')
def preview(year, month, filename):
    return static_file('{0}/{1}/{2}'.format(year, month, filename),
                       'archive/',
                       'image/tiff')


def create_index():
    if not os.path.exists(path_index):
        os.mkdir(path_index)

    if not index.exists_in(path_index):
        create_in(path_index, schema)


@command
def runserver():
    webbrowser.open_new_tab('http://localhost:8080/')
    run(host='localhost', port=8080, reloader=True)


def main():
    p = ArghParser()
    p.add_commands([scan, runserver])
    p.dispatch()


if __name__ == '__main__':
    main()
