import argparse
import base64
import colorama
import json
import sys
import httplib2
import socket
from contextlib import contextmanager

import apiclient.errors
from oauth2client import gce
from apiclient.discovery import build
from oauth2client import client
from oauth2client import file as oauth2client_file
from oauth2client import tools


class ColorString(str):
  color = None

  @classmethod
  def create(cls, string, color):
    s = cls(string)
    s.color = color
    s.string = string
    return s

  def __str__(self):
    if self.color:
      return self.color + self.string + colorama.Fore.RESET
    else:
      return self.string


def list_topics(service, args):
  return service.topics().list(
      query='cloud.googleapis.com/project in (/projects/%s)' % args.proj
      ).execute()


def create_topic(service, args):
  body = {
      'name': '/topics/%s/%s' % (args.proj, args.topic_name)
  }
  try:
    return service.topics().create(body=body).execute()
  except apiclient.errors.HttpError as e:
    if json.loads(e.content)['error']['errors'][0]['reason'] == 'alreadyexists':
      raise
    elif not args.success_if_exists:
      raise


def delete_topic(service, args):
  topic = '/topics/%s/%s' % (args.proj, args.topic_name)
  return service.topics().delete(topic=topic).execute()


def publish_message(service, args):
  fileobj = sys.stdin
  if args.from_file:
    fileobj = open(args.from_file)
  with fileobj as fileobj:
    data = fileobj.read()

  body = {
      'topic': '/topics/%s/%s' % (args.proj, args.topic_name),
      'messages': [{
        'data': base64.b64encode(data),
        'label': [
          {'key': 'host', 'strValue': socket.gethostname()},
          {'key': 'datatype', 'strValue': 'arbitrary'},
          {'key': 'sending_service', 'strValue': 'submit_event.py'},
        ],
      }],
  }
  return service.topics().publishBatch(body=body).execute()


def list_subscriptions(service, args):
  return service.subscriptions().list(
      query='cloud.googleapis.com/topic in (/projects/%s/%s)' % (
        args.proj, args.topic_name)
      ).execute()


@contextmanager
def subcommand(subparser, command, help):
  parser = subparser.add_parser(
      ColorString.create(command, colorama.Fore.GREEN), help=help)
  yield parser.add_subparsers(help='%s subcommands' % command)


def add_command(subparser, command, help, func):
  parser = subparser.add_parser(
      ColorString.create(command, colorama.Fore.GREEN), help=help)
  parser.set_defaults(func=func)
  return parser


def main():
  colorama.init()
  scope='https://www.googleapis.com/auth/pubsub https://www.googleapis.com/auth/cloud-platform'

  CLIENT_ID = '683701591616-tfv414nig13q0i6b6bo8braibfpquvgc.apps.googleusercontent.com'
  CLIENT_SECRET = 'Uit9SGtkJR-aeEGs9DfL4DMz'

  # Parse OAuth command line arguments
  parser = argparse.ArgumentParser(parents=[tools.argparser])
  parser.add_argument('--proj', default='chrome-infra-event-stream',
                      help='which project to use')

  subparsers = parser.add_subparsers(help='subcommands')

  publish_parser = add_command(
    subparsers, 'publish', 'publish a message', publish_message)
  publish_parser.add_argument(
      'topic_name', type=str, help='the topic to publish to')
  publish_parser.add_argument(
      '--from-file', type=str, help='read from a file instead of stdin')

  with subcommand(subparsers, 'topics', 'commands on topics') as subparser:
    add_command(subparser, 'list', 'list topics', list_topics)


    create_topic_parser = add_command(
      subparser, 'create', 'create a topic', create_topic)
    create_topic_parser.add_argument(
        'topic_name', type=str, help='the topic to create')
    create_topic_parser.add_argument(
        '--success-if-exists', action='store_true',
        help='don\t return failure if the topic already exists')

    delete_topic_parser = add_command(
      subparser, 'delete', 'delete a topic', delete_topic)
    delete_topic_parser.add_argument(
        'topic_name', type=str, help='the topic to delete')

  with subcommand(
      subparsers, 'subscriptions', 'commands on subscriptions') as subparser:
    add_command(subparser, 'list', 'list subscriptions', list_subscriptions)

  args = parser.parse_args()

  # Check if we already have a file with OAuth credentials
  storage = oauth2client_file.Storage('pubsub_auth.dat')
  credentials = storage.get()
  if credentials is None or credentials.invalid:
    # Start local server, redirect user to authentication page, receive OAuth
    # credentials on the local server, and store credentials in file
    flow = client.OAuth2WebServerFlow(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scope=scope)
    credentials = tools.run_flow(flow, storage, args)
  http = credentials.authorize(httplib2.Http())
  service = build('pubsub', 'v1beta1', http=http)

  print json.dumps(args.func(service, args), indent=2)

if __name__ == '__main__':
  sys.exit(main())
