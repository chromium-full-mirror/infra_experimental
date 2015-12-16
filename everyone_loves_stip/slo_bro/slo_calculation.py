import argparse
import base64
import collections
import datetime
import pytz
import requests

from jinja2 import Environment

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

import cq_pb2
from google.protobuf import text_format


def last_sunday():
   last_sunday = datetime.datetime.utcnow()
   while last_sunday.weekday() != 6:  # Sunday is 6.
     last_sunday -= datetime.timedelta(days=1)
   last_sunday = last_sunday.replace(
       hour=0, minute=0, second=0, microsecond=0)  

   return last_sunday


HourSpan = collections.namedtuple('HourSpan', [
  'start_hr',  # 0 - 23.
  'start_tz',  # 'America/Los_Angeles' or 'Europe/Berlin'.
  'end_hr',
  'end_tz',
])


def utctimestamp(dt):
  epoch = datetime.datetime.utcfromtimestamp(0)
  return (dt - epoch).total_seconds()


def slo_one_week(start_sunday, slo_spec):
  epoch = datetime.datetime.utcfromtimestamp(0).replace(tzinfo=pytz.UTC)
  ranges = []
  for i, spec in enumerate(slo_spec):
    if spec is not None:
      start = start_sunday + datetime.timedelta(days=i)
      spec_start = (start + datetime.timedelta(hours=spec.start_hr)).replace(
        tzinfo=pytz.timezone(spec.start_tz))
      spec_end = (start + datetime.timedelta(hours=spec.end_hr)).replace(
        tzinfo=pytz.timezone(spec.end_tz))
      ranges.append([
        (spec_start - epoch).total_seconds() * 1000,
        (spec_end - epoch).total_seconds() * 1000,
      ])
  return ranges



def get_builders():
  cq_config = base64.b64decode(
      requests.get(
        'https://luci-config.appspot.com/_ah/api/config/v1/config_sets/'
        'projects%2Fchromium%2Frefs%2Fheads%2Fmaster/config/cq.cfg'
      ).json()['content'])

  config = cq_pb2.Config()
  text_format.Merge(cq_config, config)

  builders = []
  if config.verifiers.HasField('try_job'):
    for bucket in config.verifiers.try_job.buckets:
      for builder in bucket.builders:
        if not builder.HasField('experiment_percentage'):
          builders.append(builder.name)
  return builders



def main(project_id, table):
    slo_spec = [
        None,  # Sunday.
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        None,  # Saturday.
    ]

    builders = get_builders()

    # Grab the application's default credentials from the environment.
    credentials = GoogleCredentials.get_application_default()
    # Construct the service object for interacting with the BigQuery API.
    dates = slo_one_week(last_sunday() - datetime.timedelta(days=7), slo_spec)
    bigquery_service = build('bigquery', 'v2', credentials=credentials)

    QUERY = """
      SELECT builder,
          ROW_NUMBER() OVER (
              PARTITION BY builder ORDER BY
              total_execution_minutes) as pre_percentile,
          quantiles(total_duration_s, 101) / 60.0 as total_execution_minutes
      FROM (

        SELECT builder, total_duration_s
        FROM {{ table }}
        WHERE
            (
            {% for date in dates %}
              (build_sched_msec > {{ date[0] }} AND
                build_sched_msec < {{ date[1] }})
              {% if not loop.last %}
              OR
              {% endif %}
            {% endfor %}
            ) 
            AND LEFT(master, LENGTH('master.tryserver.')) = 'master.tryserver.'
            AND (
              {% for builder in builders %}
                builder = '{{ builder }}'
                {% if not loop.last %}
                OR
                {% endif %}
              {% endfor %}
            ))
        GROUP BY builder
    """

    try:
        query_request = bigquery_service.jobs()
        query_data = {
            'query': Environment().from_string(QUERY).render(
              dates=dates,
              builders=builders,
              table=table)
        }

        print query_data['query']

        query_response = query_request.query(
            projectId=project_id,
            body=query_data).execute()

        print('Query Results:')
        for row in query_response['rows']:
            print row
            #print('\t'.join(field['v'] for field in row['f']))

    except HttpError as err:
        print('Error: {}'.format(err.content))
        raise err


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('project_id', help='Your Google Cloud Project ID.')
    parser.add_argument('table', help='Build data table.')

    args = parser.parse_args()

    main(args.project_id, args.table)
