#!/usr/bin/env python
# -*- coding: utf-8 -*-
import atexit
import json
import shutil
import tempfile

import click
import dotmap
import sh
import yaml

from . import utils as _utils

from . import mirrorer

@click.group()
@click.option('--debug/--no-debug', envvar='DEBUG', default=False)
@click.option('--default-log-level', '--log-level', default='DEBUG')
@click.option('--file-log-level', default=None)
@click.option('--console-log-level', default=None)
@click.pass_context
def cli(ctx, debug, default_log_level, file_log_level, console_log_level):
    ctx.ensure_object(dotmap.DotMap)
    ctx.obj.debug = debug
    ctx.obj.repo_root = str(sh.git('rev-parse --show-toplevel'.split())).strip()
    ctx.obj.log = _utils.setup_logging(default_log_level=default_log_level, file_log_level=file_log_level, console_log_level=console_log_level)
    ctx.obj.temp_dir = tempfile.TemporaryDirectory()

    @atexit.register
    def cleanup():
        shutil.rmtree(ctx.obj.temp_dir.name)


# git group
@click.group()
@click.pass_context
def gruntwork(ctx):
    pass


@gruntwork.command()
@click.option('--profile-file', '-p', required=True, type=click.Path())
@click.pass_context
def mirror(ctx, profile_file):
    m = mirrorer.Mirrorer(profile_path=profile_file)
    m.mirror()
    # for mirror in m.mirrors:
    #     print(mirror.__dict__)

    # r = m.source.repos

    # print(json.dumps(r, indent=4))
    # target_source = r[0]
    # for mirror in m.mirrors:
    #     e = mirror.repo_exists('terraform-aws-vpc')
    #     x = mirror.repo_upsert(source_repo=target_source)

if __name__ == '__main__':
    cli.add_command(gruntwork)
    cli(obj={})
