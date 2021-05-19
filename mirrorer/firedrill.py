# -*- coding: utf-8 -*-
import json
import re

import requests

ACCESS_TOKEN = '7a285e8f48f85958dd04257966be69c6c57e519c'
BASE_URL = 'https://www-github3.cisco.com/api/v3'

PUBLIC_ACCESS_TOKEN = '4d3ad44f6df3447de0e977ad67b04a8787b8e03c'
PUBLIC_BASE_URL = 'https://api.github.com'


def get_session(access_token=None, base_url=None):
    headers = {
        'Authorization': 'token {}'.format(access_token),
        'Accept': 'application/vnd.github.mercy-preview+json'
    }
    session = requests.Session()
    session.headers.update(headers)
    session.base_url = base_url
    return session

def parse_links(headers=None):
    if 'Link' not in headers:
        return None
    link_str = headers['Link']
    _links = link_str.replace(' ', '').split(',')
    base_pattern = r'^<(.*)>;rel="(.*)"$'
    ret = {}
    for l in _links:
        m = re.match(base_pattern, l)
        if m:
            url, rel = m.groups()[0], m.groups()[1]
            ret[rel] = url
    return ret

def search_repos(session=None, url=None, search_query=None):
    repos = []
    if not url:
        url = "{base_url}/search/repositories?q={search_query}".format(base_url=session.base_url, search_query=search_query)
    req = session.get(url)
    if not req.ok:
        raise ValueError('Failed search repos repos [%s]. %s', url, req.reason)

    data = req.json()
    repos = repos + data['items']

    links = parse_links(req.headers)
    if links and 'next' in links:
        repos = repos + search_repos(session=session, url=links['next'])
    return repos




def transfer(session=None, repo=None, new_owner=None):
    data = {"new_owner": new_owner}
    repo_name = repo['name']
    old_owner = repo['owner']['login']
    url = "{base_url}/repos/{owner}/{repo}/transfer".format(base_url=session.base_url, owner=old_owner, repo=repo_name)
    req = session.post(url=url, data=json.dumps(data))
    print('Transfering repo %s/%s', old_owner, repo_name)
    if not req.ok:
        raise ValueError('Failed to transfer repo %s/%s', old_owner, repo_name)

    print(req.status_code)


def rename(session=None, repo=None):
    old_name = repo['name']
    owner = repo['owner']['login']
    pattern = r'^gruntwork-(.+)$'

    m = re.match(pattern=pattern, string=old_name)

    if not m:
        print("skipping renaming of %s", old_name)
        return
    else:
        new_name = m.groups()[0]
        print('renaming repo %s/%s->%s' % (old_name, owner, new_name))
        url = "{base_url}/repos/{owner}/{repo}".format(base_url=session.base_url, owner=owner, repo=old_name)
        data = {'name': new_name}
        req = session.patch(url=url, data=json.dumps(data))
        if not req.ok:
            raise ValueError('Failed to transfer repo %s/%s', old_owner, repo_name)

        print(req.status_code)


def update_collaborations(session=None, owner=None, repo=None, collaborator=None):
    # url = "{base_url}/repos/{owner}/{repo}/collaborators/{collaborator}".format(base_url=session.base_url, owner=owner, repo=repo, collaborator=collaborator)
    # url = "{base_url}/orgs/{owner}/teams/{collaborator}/repos/{owner}/{repo}".format(base_url=session.base_url, owner=owner, repo=repo, collaborator=collaborator)
    # url = "{base_url}/orgs/{owner}/teams".format(base_url=session.base_url, owner=owner, repo=repo, collaborator=collaborator)
    url = "{base_url}/teams/109/repos/{owner}/{repo}".format(base_url=session.base_url, owner=owner, repo=repo, collaborator=collaborator)
    """/orgs/:org/teams"""
    '''/orgs/:org/teams/:team_slug/repos/:owner/:repo'''
    """/orgs/:org/teams/:team_slug/repos/:owner/:repo"""
    """/orgs/:org/teams/:team_slug/repos"""
    """/teams/:team_id/repos/:owner/:repo"""

    params = {'permission': 'pull'}
    print(url)
    session.headers.update({'Content-Length': '0'})
    req = session.put(url=url, params=params)
    # req = session.get(url=url)
    # print(json.dumps(req.json(), indent=4))
    if not req.ok:
        print(req.status_code)
        print(req.reason)
        raise ValueError('Failed to add collaborator repo %s/%s' % (owner, repo))
    #

    print(req.status_code)

"""
 'Link': '<https://api.github.com/search/repositories?q=is%3Aprivate+org%3Agruntwork-io&page=2>; rel="next", <https://api.github.com/search/repositories?q=is%3Aprivate+org%3Agruntwork-io&page=2>; rel="last"', 
 'Link': '<https://api.github.com/search/repositories?q=is%3Aprivate+org%3Agruntwork-io&page=1>; rel="prev", <https://api.github.com/search/repositories?q=is%3Aprivate+org%3Agruntwork-io&page=1>; rel="first"',

"""
def update_branch_protections():
    data = {
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismissal_restrictions": {
                "teams": [
                    "gruntwork-io"
                ]
            },
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": True,
            "required_approving_review_count": 1
        },
        "restrictions": {
            "users": [
                "octocat"
            ],
            "teams": [
                "justice-league"
            ],
            "apps": [
                "super-ci"
            ]
        },
        "required_linear_history": True,
        "allow_force_pushes": False,
        "allow_deletions": False
    }
    pass


def go():
    s = get_session(access_token=PUBLIC_ACCESS_TOKEN, base_url=PUBLIC_BASE_URL)
    s = get_session(access_token=ACCESS_TOKEN, base_url=BASE_URL)

    repos = search_repos(session=s, search_query='is:private+org:gruntwork-io')
    print(len(repos))
    print(json.dumps(repos, indent=4))


go()
