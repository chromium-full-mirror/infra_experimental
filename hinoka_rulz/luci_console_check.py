#!/usr/bin/env python

import argparse
import httplib2
import sys
import json
import urlparse
import os
import cookielib
import base64
import logging
import project_pb2 as proj
from google.protobuf import text_format

LOGGER = logging.getLogger()

def CreateHttpConn(host, path, reqtype='GET', headers=None, body=None):
  """Opens an https connection to a gerrit service, and sends a request."""
  headers = headers or {}
  bare_host = host.partition(':')[0]

  auth = CookiesAuthenticator().get_auth_header(bare_host)
  if auth:
    headers.setdefault('Authorization', auth)
  else:
    LOGGER.debug('No authorization found for %s.' % bare_host)

  url = path
  if not url.startswith('/'):
    url = '/' + url
  if 'Authorization' in headers and not url.startswith('/a/'):
    url = '/a%s' % url

  if body:
    body = json.JSONEncoder().encode(body)
    headers.setdefault('Content-Type', 'application/json')
  if LOGGER.isEnabledFor(logging.DEBUG):
    LOGGER.debug('%s %s://%s%s' % (reqtype, 'https', host, url))
    for key, val in headers.iteritems():
      if key == 'Authorization':
        val = 'HIDDEN'
      LOGGER.debug('%s: %s' % (key, val))
    if body:
      LOGGER.debug(body)
  conn = httplib2.Http()
  conn.req_host = host
  conn.req_params = {
      'uri': urlparse.urljoin('%s://%s' % ('https', host), url),
      'method': reqtype,
      'headers': headers,
      'body': body,
  }
  return conn

class CookiesAuthenticator(object):
  """Authenticator implementation that uses ".netrc" or ".gitcookies" for token.

  Expected case for developer workstations.
  """

  def __init__(self):
    self.gitcookies = self._get_gitcookies()

  @classmethod
  def get_new_password_url(cls, host):
    assert not host.startswith('http')
    # Assume *.googlesource.com pattern.
    parts = host.split('.')
    if not parts[0].endswith('-review'):
      parts[0] += '-review'
    return 'https://%s/new-password' % ('.'.join(parts))

  @classmethod
  def get_new_password_message(cls, host):
    assert not host.startswith('http')
    # Assume *.googlesource.com pattern.
    parts = host.split('.')
    if not parts[0].endswith('-review'):
      parts[0] += '-review'
    url = 'https://%s/new-password' % ('.'.join(parts))
    return 'You can (re)generate your credentials by visiting %s' % url

  @classmethod
  def get_gitcookies_path(cls):
    if os.getenv('GIT_COOKIES_PATH'):
      return os.getenv('GIT_COOKIES_PATH')
    return os.path.join(os.environ['HOME'], '.gitcookies')

  @classmethod
  def _get_gitcookies(cls):
    gitcookies = {}
    path = cls.get_gitcookies_path()
    if not os.path.exists(path):
      return gitcookies

    try:
      f = open(path, 'rb')
    except IOError:
      return gitcookies

    with f:
      for line in f:
        try:
          fields = line.strip().split('\t')
          if line.strip().startswith('#') or len(fields) != 7:
            continue
          domain, xpath, key, value = fields[0], fields[2], fields[5], fields[6]
          if xpath == '/' and key == 'o':
            login, secret_token = value.split('=', 1)
            gitcookies[domain] = (login, secret_token)
        except (IndexError, ValueError, TypeError) as exc:
          LOGGER.warning(exc)

    return gitcookies

  def _get_auth_for_host(self, host):
    for domain, creds in self.gitcookies.iteritems():
      if cookielib.domain_match(host, domain):
        return (creds[0], None, creds[1])
    return self.netrc.authenticators(host)

  def get_auth_header(self, host):
    auth = self._get_auth_for_host(host)
    if auth:
      return 'Basic %s' % (base64.b64encode('%s:%s' % (auth[0], auth[2])))
    return None

  def get_auth_email(self, host):
    """Best effort parsing of email to be used for auth for the given host."""
    auth = self._get_auth_for_host(host)
    if not auth:
      return None
    login = auth[0]
    # login typically looks like 'git-xxx.example.com'
    if not login.startswith('git-') or '.' not in login:
      return None
    username, domain = login[len('git-'):].split('.', 1)
    return '%s@%s' % (username, domain)

def get_buildermap(buildermap_url):
  p = urlparse.urlparse(buildermap_url)
  conn = CreateHttpConn(p.hostname, p.path + '?format=TEXT')
  response, contents = conn.request(**conn.req_params)
  if response.status != 200:
    raise Exception('Bad response: %s' % response)
  return json.loads(base64.b64decode(contents))

def get_console_def(url):
  p = urlparse.urlparse(url)
  conn = CreateHttpConn(p.hostname, p.path + '?format=TEXT')
  response, contents = conn.request(**conn.req_params)
  if response.status != 200:
    raise Exception('Bad response: %s' % response)
  return text_format.Parse(base64.b64decode(contents), proj.Project())

def rearrange(buildermap):
  masters = {}
  for builder in buildermap:
    name = builder['mastername']
    if name.startswith('master.'):
      name = name[len('master.'):]
    if name not in masters:
      masters[name] = []
    masters[name].append(builder['builder'])
  return masters


def check(buildermap_url, console_def_url):
  buildermap = get_buildermap(buildermap_url)
  masters = rearrange(buildermap)
  console_def = get_console_def(console_def_url)
  for console in console_def.consoles:
    print 'Processing %s...' % console.id,
    if console.id not in masters:
      print 'Not found'
      continue
    plus = []
    minus = []
    builders = [builder.name[0].split('/')[2] for builder in console.builders]
    for builder in builders:
      if builder not in masters[console.id]:
        minus.append(builder)
    for builder in masters[console.id]:
      if builder not in builders:
        plus.append(builder)
    if plus or minus:
      print 'DIFF FOUND'
      for builder in plus:
        print '  + %s' % builder
      for builder in minus:
        print '  - %s' % builder
    else:
      print 'OK'


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument(
    '-b', '--buildermap-url',
    default='https://chrome-internal.googlesource.com/infradata/hosts/+/master/buildermap.json')
  parser.add_argument(
    '-c', '--console', default='https://chromium.googlesource.com/chromium/src/+/infra/config/luci-milo.cfg')
  args = parser.parse_args()
  return check(args.buildermap_url, args.console)

if __name__ == '__main__':
  sys.exit(main())
