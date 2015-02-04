import argparse
import json
import sys
import httplib2
from contextlib import contextmanager

import apiclient.errors
from oauth2client import gce
from apiclient.discovery import build
from oauth2client import client
from oauth2client import file as oauth2client_file
from oauth2client import tools


def list_topics(service, args):
  print service.topics().list(
      query='cloud.googleapis.com/project in (/projects/%s)' % args.proj
      ).execute()


def create_topic(service, args):
  body = {
      'name': '/topics/%s/%s' % (args.proj, args.topic_name)
  }
  try:
    print service.topics().create(body=body).execute()
  except apiclient.errors.HttpError as e:
    if json.loads(e.content)['error']['errors'][0]['reason'] == 'alreadyexists':
      raise
    elif not args.success_if_exists:
      raise


def delete_topic(service, args):
  topic = '/topics/%s/%s' % (args.proj, args.topic_name)
  print service.topics().delete(topic=topic).execute()


@contextmanager
def subcommand(subparser, command, help):
  parser = subparser.add_parser(command, help=help)
  yield parser.add_subparsers(help='%s subcommands' % command)


def add_command(subparser, command, help, func):
  parser = subparser.add_parser(command, help=help)
  parser.set_defaults(func=func)
  return parser


def main():
  scope='https://www.googleapis.com/auth/pubsub https://www.googleapis.com/auth/cloud-platform'

  CLIENT_ID = '683701591616-tfv414nig13q0i6b6bo8braibfpquvgc.apps.googleusercontent.com'
  CLIENT_SECRET = 'Uit9SGtkJR-aeEGs9DfL4DMz'

  # Parse OAuth command line arguments
  parser = argparse.ArgumentParser(parents=[tools.argparser])
  parser.add_argument('--proj', default='chrome-infra-event-stream',
                      help='which project to use')

  subparsers = parser.add_subparsers(help='subcommands')
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

  args.func(service, args)

if __name__ == '__main__':
  sys.exit(main())
