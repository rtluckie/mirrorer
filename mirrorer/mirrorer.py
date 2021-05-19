# -*- coding: utf-8 -*-
import json
import logging
import os
import pathlib

import git
import requests
import sh

from . import utils

log = logging.getLogger(__name__)


class Mirrorer:
    def __init__(self, cache_path=None, config_path=None, profile_path=None):

        if not cache_path:
            self.cache_path = os.path.join(pathlib.Path.home(), '.cache', 'mirrorer')
        os.makedirs(self.cache_path, exist_ok=True)

        if not config_path:
            config_path = os.path.join(pathlib.Path.home(), '.config', 'mirrorer', 'config.yaml')
        self.config_path = config_path
        self._config = None

        if not profile_path:
            raise ValueError('Profile is required')
        self.profile_path = profile_path
        self._profile = None

        self._mirrors = None
        self._source = None

    @property
    def config(self):
        if not self._config:
            self._config = utils.load_config(self.config_path)
        return self._config

    @property
    def profile(self):
        if not self._profile:
            self._profile = utils.load_config(self.profile_path)
        return self._profile

    @property
    def source(self):
        if not self._source:
            _source_data = {}
            for k, v in self.profile['source'].items():
                _source_data[k] = v
            profile = _source_data['profile']
            profile_data = self.config[profile]
            for pk, pv in profile_data.items():
                _source_data[pk] = pv
            self._source = Source(**_source_data)
        return self._source

    @property
    def mirrors(self):
        if not self._mirrors:
            aliases = []
            self._mirrors = []
            _mirrors = self.profile['mirrors']
            _mirrors_data = {}
            for k, v in _mirrors.items():
                _mirrors_data[k] = v
            for k in _mirrors_data:
                profile = _mirrors_data[k]['profile']
                profile_data = self.config[profile]
                for pk, pv in profile_data.items():
                    _mirrors_data[k][pk] = pv
            for k, v in _mirrors_data.items():
                alias = k
                if alias in aliases:
                    raise ValueError('aliases must be unique')
                mirror_obj = Mirror(**v)
                mirror_obj.alias = alias
                self._mirrors.append(mirror_obj)
        return self._mirrors

    @staticmethod
    def get_slug(string):
        return utils.get_slug(string)

    def clone(self, repo):
        url = repo['ssh_url']
        slug = utils.get_slug(url)
        location = os.path.join(self.cache_path, slug)
        if os.path.isdir(location):
            repo = git.Repo(location)
            os.chdir(location)
            sh.git('checkout master'.split())
            sh.git('pull origin master  '.split())
        else:
            repo = git.Repo.clone_from(url=url, to_path=location, no_checkout=False)
        return repo, location

    def mirror(self):
        for source_repo in self.source.repos:
            repo_obj, location = self.clone(source_repo)
            for mirror in self.mirrors:
                mirror_repo = mirror.repo_upsert(source_repo)
                url = mirror_repo['ssh_url']
                remote_name = "{alias}".format(alias=mirror.alias)
                if not remote_name in repo_obj.remotes:
                    remote = repo_obj.create_remote(remote_name, url)
                else:
                    remote = repo_obj.remote(remote_name)
                remote.fetch()
                os.chdir(location)
                branches = repo_obj.branches
                for branch in ['main', 'gruntwork']:
                    if branch in branches:
                        sh.git('checkout {}'.format(branch).split())
                    else:
                        sh.git('checkout -b {}'.format(branch).split())
                    sh.git('rebase origin/master'.split())
                    sh.git('push {alias} {branch} --tags'.format(alias=mirror.alias, branch=branch).split())


class MirrorerBaseObject:
    def __init__(self, **kwargs):
        self.access_token = None
        self.base_url = None
        self.org = None
        for k, v in kwargs.items():
            setattr(self, k, v)
        self._session = None

    @property
    def session(self):
        if not self._session:
            headers = {
                'Authorization': 'token {}'.format(self.access_token),
                'Accept': 'application/vnd.github.mercy-preview+json'
            }
            session = requests.Session()
            session.headers.update(headers)
            self._session = session
        return self._session


class Source(MirrorerBaseObject):

    def __init__(self, **kwargs):
        self.search_query = None
        super().__init__(**kwargs)

    @property
    def repos(self):
        url = "{base_url}/search/repositories?q={search_query}".format(base_url=self.base_url, search_query=self.search_query)
        req = self.session.get(url)

        data = req.json()
        if not req.ok:
            raise ValueError('Failed to get source repos [%s]. %s', url, req.reason)
        elif data['incomplete_results']:
            raise ValueError('Incomplete results when getting source repos [%s].', url, req.reason)
        return data['items']


class Mirror(MirrorerBaseObject):

    def __init__(self, **kwargs):
        self.prefix = None
        super().__init__(**kwargs)

    def repo_exists(self, repo_name=None):
        url = "{base_url}/search/repositories?q=repo:{org}/{prefix}{repo_name}".format(base_url=self.base_url, org=self.org, prefix=self.prefix, repo_name=repo_name)
        req = self.session.get(url)
        if req.status_code == 422 and not req.ok:
            return {}
        elif req.ok and req.json()['total_count'] == 1:
            return req.json()['items'][0]

    def repo_branch_proections_upsert(self, source_repo):
        pass

    def delete_branch_restriction(self, source_repo=None, branch_name=None):
        log.info('deleting branch restriction')
        name = "{prefix}{name}".format(prefix=self.prefix, name=source_repo['name'])
        url = "{base_url}/repos/{owner}/{repo}/branches/{branch_name}/protection".format(base_url=self.base_url, owner=self.org, repo=name, branch_name=branch_name)
        req = self.session.delete(url=url)

    def repo_upsert(self, source_repo=None):

        defaults = {
            "name": None,
            "description": None,
            "homepage": None,
            "private": True,
            "has_issues": True,
            "has_projects": False,
            "has_wiki": True,
            "default_branch": 'main',
            "allow_squash_merge": True,
            "allow_merge_commit": False,
            "allow_rebase_merge": True,
            "delete_branch_on_merge": True,
        }
        repo_data = defaults
        for key in ['description', 'homepage']:
            if key in source_repo:
                repo_data[key] = source_repo[key]

        name = "{prefix}{name}".format(prefix=self.prefix, name=source_repo['name'])
        log.debug('Upserting repo %s', name)
        repo_data['name'] = name
        for k, v in defaults.items():
            if k not in repo_data and defaults[k] != None:
                repo_data[k] = v
        repo_data = dict(sorted(repo_data.items()))
        mirror_repo = self.repo_exists(source_repo['name'])

        if mirror_repo:
            log.info('repo exists')
            url = "{base_url}/repos/{owner}/{repo}".format(base_url=self.base_url, owner=self.org, repo=name)
            req = self.session.patch(url=url, data=json.dumps(repo_data))
            if not req.ok:
                raise ValueError('Failed to update repo')
            return req.json()
        else:
            log.info('repo does not exist')
            url = "{base_url}/orgs/{org}/repos".format(base_url=self.base_url, org=self.org)
            req = self.session.post(url=url, data=json.dumps(repo_data))
            if not req.ok:
                raise ValueError('Failed to create repo')
            return req.json()
