# -*- coding: utf-8 -*-
import json
import logging
import os
import pathlib
import re

import slugify
import yaml



def setup_logging(name='mirrorer', default_log_level='DEBUG', file_log_level='DEBUG', console_log_level=None):
    if not file_log_level and default_log_level:
        file_log_level = default_log_level
    if not console_log_level and default_log_level:
        console_log_level = default_log_level
    log = logging.getLogger(name)
    log.setLevel(default_log_level)
    formatter = logging.Formatter(fmt='%(asctime)s:%(msecs)-4d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s', datefmt='%Y.%m.%d %H:%M:%S')
    file_handler = logging.FileHandler('%s.log' % name)
    file_handler.setLevel(file_log_level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_log_level)
    # Add formatter to handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    # add the handlers to the logger
    log.addHandler(file_handler)
    log.addHandler(console_handler)
    return log


def load_config(fpath: str = None) -> dict:
    if not fpath:
        fpath = os.path.join(pathlib.Path.home(), '.config', 'mirrorer', 'config.yaml')
    logging.debug("Loading config from %s", fpath)
    with open(fpath) as fin:
        ret = yaml.safe_load(fin.read())
    return ret


def clean_uri(uri=None):
    uri = re.sub(r'(https://|http://|git@)', "", uri)
    pattern = r'^(.+)\.git$'
    m = re.match(pattern, uri)
    if m:
        uri = m.groups()[0]
    return uri


def get_slug(s=None, clean=True):
    ret = s
    if clean:
        ret = clean_uri(ret)
    return slugify.slugify(ret)
