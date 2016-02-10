# Copyright © 2016 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

'''
command-line interface
'''

import argparse
import collections
import io
import json
import re
import shutil
import sys
import urllib.request

import lib.colors
import lib.pager

user_agent = 'trava (https://github.com/jwilk/trava)'

def get(url, headers=()):
    headers = dict(headers)
    headers.update(
        {'User-Agent': user_agent}
    )
    request = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(request)

def get_json(url, headers=()):
    headers = dict(headers)
    headers.update(
        {'Content-Type': 'application/vnd.travis-ci.2+json'}
    )
    with get(url, headers) as fp:
        with io.TextIOWrapper(fp) as tfp:
            return json.load(tfp)

url_re = re.compile(
    r'''
    \A
    https://travis-ci.org/
    (?P<project>[\w-]+/[\w-]+)/
    (?:
      builds/(?P<build>\d+)
    | jobs/(?P<job>\d+)
    )
    \Z
    ''',
    re.VERBOSE
)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('url', metavar='URL')
    options = ap.parse_args()
    match = url_re.match(options.url)
    if match is None:
        ap.error('invalid URL')
    with lib.pager.autopager():
        _main(match)

def _main(match):
    project = match.group('project')
    build_id = match.group('build')
    if build_id is not None:
        return show_build(project, build_id)
    job_id = match.group('job')
    if job_id is not None:
        return show_job(job_id)
    raise NotImplementedError

def show_build(project, build_id):
    url = 'https://api.travis-ci.org/repos/{project}/builds/{id}'
    url = url.format(project=project, id=build_id)
    data = get_json(url)
    config_coll = collections.defaultdict(set)
    for job in data['matrix']:
        for key, value in job['config'].items():
            if isinstance(value, (dict, list)):
                continue
            config_coll[key].add(value)
    for job in data['matrix']:
        template = '#{number} {config}'
        if job['finished_at'] is None:
            template = '{t.yellow}' + template
        if job['result']:
            template = '{t.bold}{t.red}' + template
        template = template + '{t.off}'
        config = []
        for key, value in sorted(job['config'].items()):
            if key.startswith('.'):
                continue
            if isinstance(value, (dict, list)):
                continue
            if len(config_coll[key]) == 1:
                continue
            config += ['{key}={value}'.format(key=key, value=value)]
        config = ' '.join(config)
        lib.colors.print(template, number=job['number'], config=config)
        url = 'https://travis-ci.org/{project}/jobs/{id}'
        url = url.format(project=project, id=job['id'])
        template = '{t.cyan}'
        if job['result']:
            template += '{t.bold}'
        template += '{url}{t.off}'
        lib.colors.print(template, url=url, space='')
        print()

def show_job(job_id):
    url = 'https://api.travis-ci.org/jobs/{id}/log.txt'
    url = url.format(id=job_id)
    with get(url) as fp:
        shutil.copyfileobj(fp, sys.stdout.buffer)

__all__ = ['main']

# vim:ts=4 sts=4 sw=4 et
