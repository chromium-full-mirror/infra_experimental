import argparse
import base64
import calendar
import colorama
import datetime
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


def get_topic(service, args):
  topic = '/topics/%s/%s' % (args.proj, args.topic_name)
  return service.topics().get(topic=topic).execute()


def publish_message(service, args):
  fileobj = sys.stdin
  if args.from_file:
    fileobj = open(args.from_file)
  with fileobj as fileobj:
    data = fileobj.read()

  utc_timestamp = calendar.timegm(datetime.datetime.utcnow().utctimetuple())
  utc_date = datetime.datetime.utcnow().isoformat()

  body = {
      'topic': '/topics/%s/%s' % (args.proj, args.topic_name),
      'messages': [{
        'data': base64.b64encode(data),
        'label': [
          {'key': 'host', 'strValue': socket.gethostname()},
          {'key': 'datatype', 'strValue': 'arbitrary'},
          {'key': 'sending_service', 'strValue': 'submit_event.py'},
          {'key': 'sending_utc_timestamp', 'numValue': utc_timestamp},
          {'key': 'sending_utc_date', 'strValue': utc_date},
        ],
      }],
  }
  return service.topics().publishBatch(body=body).execute()


def list_subscriptions(service, args):
  query = 'cloud.googleapis.com/project in (/projects/%s)' % args.proj
  if args.topic_name:
    query='pubsub.googleapis.com/topic in (/topics/%s/%s)' % (
          args.proj, args.topic_name)
  return service.subscriptions().list(query = query).execute()


def get_subscription(service, args):
  subscription = '/subscriptions/%s/%s' % (args.proj, args.sub_id)
  return service.subscriptions().get(subscription=subscription).execute()


def create_subscription(service, args):
  body = {
      'name': '/subscriptions/%s/%s' % (args.proj, args.sub_id),
      'topic': '/topics/%s/%s' % (args.proj, args.topic_name),
  }
  if args.push:
    body['pushConfig'] = {'pushEndpoint': args.push}

  try:
    return service.subscriptions().create(body=body).execute()
  except apiclient.errors.HttpError as e:
    if json.loads(e.content)['error']['errors'][0]['reason'] == 'alreadyexists':
      raise
    elif not args.success_if_exists:
      raise


def delete_subscription(service, args):
  subscription = '/subscriptions/%s/%s' % (args.proj, args.sub_id)
  return service.subscriptions().delete(subscription=subscription).execute()


def ack_message_ids(service, proj, sub_id, ids):
  body = {
      'subscription': '/subscriptions/%s/%s' % (proj, sub_id),
      'ackId': ids,
  }
  return service.subscriptions().acknowledge(body=body).execute()


def pull_from_subscription(service, args):
  body = {
      'subscription': '/subscriptions/%s/%s' % (args.proj, args.sub_id),
      'returnImmediately': not args.wait,
      'maxEvents': args.max,
  }
  results = service.subscriptions().pullBatch(body=body).execute()

  if results:
    ack_ids = [m['ackId'] for m in results['pullResponses']]
    if not args.no_ack:
      ack_message_ids(service, args.proj, args.sub_id, ack_ids)
    if args.base64unencode:
      for res in results['pullResponses']:
        message = res['pubsubEvent']['message']
        message['data'] = base64.b64decode(message['data'])

  return results
  

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
      'topic_name', help='the topic to publish to')
  publish_parser.add_argument(
      '--from-file', help='read from a file instead of stdin')

  with subcommand(subparsers, 'topics', 'commands on topics') as subparser:
    add_command(subparser, 'list', 'list topics', list_topics)

    get_topic_parser = add_command(subparser, 'get', 'get details about a topic', list_topics)
    get_topic_parser.add_argument(
        'topic_name', help='the topic to get')

    create_topic_parser = add_command(
      subparser, 'create', 'create a topic', create_topic)
    create_topic_parser.add_argument(
        'topic_name', help='the topic to create')
    create_topic_parser.add_argument(
        '--success-if-exists', action='store_true',
        help='don\t return failure if the topic already exists')

    delete_topic_parser = add_command(
      subparser, 'delete', 'delete a topic', delete_topic)
    delete_topic_parser.add_argument(
        'topic_name', help='the topic to delete')

  with subcommand(
      subparsers, 'subscriptions', 'commands on subscriptions') as subparser:
    list_sub_parser = add_command(subparser, 'list', 'list subscriptions', list_subscriptions)
    list_sub_parser.add_argument(
        '--topic_name', help='the topic the subscription is for')

    get_sub_parser = add_command(subparser, 'get', 'get details about a subscription', get_subscription)
    get_sub_parser.add_argument(
        'sub_id', help='the subscription id')

    create_sub_parser = add_command(
      subparser, 'create', 'create a subscription', create_subscription)
    create_sub_parser.add_argument(
        'topic_name', help='the topic to create a subscription for')
    create_sub_parser.add_argument(
        'sub_id', help='the subscription id')
    create_sub_parser.add_argument(
        '--success-if-exists', action='store_true',
        help='don\t return failure if the subscription already exists')
    create_sub_parser.add_argument(
        '--push', help='configure as push subscription to this endpoint')

    delete_sub_parser = add_command(
      subparser, 'delete', 'delete a subscription', delete_subscription)
    delete_sub_parser.add_argument(
        'sub_id', help='the subscription id')

    pull_sub_parser = add_command(
      subparser, 'pull', 'pull from a subscription', pull_from_subscription)
    pull_sub_parser.add_argument(
        'sub_id', help='the subscription id')
    pull_sub_parser.add_argument(
        '--wait', action='store_true',
        help='wait if no messages have arrived yet')
    pull_sub_parser.add_argument(
        '--no-ack', action='store_true',
        help='don\'t ack the messages, allowing them to be read again after '
             'deadline')
    pull_sub_parser.add_argument(
        '--max', default=100, type=int,
        help='max messages to return per pull')
    pull_sub_parser.add_argument(
        '--base64unencode', action='store_true',
        help='unencode base64 payload.')

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

  print json.dumps(args.func(service, args) or {}, indent=2)

if __name__ == '__main__':
  sys.exit(main())
