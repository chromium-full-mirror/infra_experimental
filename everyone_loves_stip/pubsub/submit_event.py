import argparse
import sys
import httplib2

from oauth2client import gce
from apiclient.discovery import build

def main():
  scope='https://www.googleapis.com/auth/pubsub https://www.googleapis.com/auth/cloud-platform'
  from oauth2client import client
  from oauth2client import file as oauth2client_file
  from oauth2client import tools

  CLIENT_ID = '683701591616-tfv414nig13q0i6b6bo8braibfpquvgc.apps.googleusercontent.com'
  CLIENT_SECRET = 'Uit9SGtkJR-aeEGs9DfL4DMz'

# Parse OAuth command line arguments
  parser = argparse.ArgumentParser(parents=[tools.argparser])
  parser.add_argument('--proj', default='chrome-infra-event-stream',
                      help='which project to use')

  flags = parser.parse_args()

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
    credentials = tools.run_flow(flow, storage, flags)
  http = credentials.authorize(httplib2.Http())
  service = build('pubsub', 'v1beta1', http=http)
  print service.topics().list(
      query='cloud.googleapis.com/project in (/projects/%s)' % flags.proj
      ).execute()

if __name__ == '__main__':
  sys.exit(main())
