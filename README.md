
## Paperstore

Paperstore is a little python script to scan and index documents

## Usage

    ./paperstore.py scan --tags=sometag

or if you want to search scanned documents:

    ./paperstore.py runserver

This will start a webserver and point your browser to http://localhost:8080/.
There you'll be provided with a search form.

## Requirements

### Commandline tools

* scanimage (either in sane or sane-utils)
* unpaper
* imagemagick
* tesseract
* libtiff

### Python

* python 2.7
* argh
* bottle

### Other

* crate
