import argparse
import base64
import collections
import datetime
import pytz
import random
import json

from jinja2 import Environment

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import GoogleCredentials

import cq_pb2
from google.protobuf import text_format

from google.appengine.api import urlfetch
from google.appengine.api import app_identity

import models

GAE_APP_ID = app_identity.get_application_id()


def last_sunday():
   last_sunday = datetime.datetime.utcnow()
   while last_sunday.weekday() != 6:  # Sunday is 6.
     last_sunday -= datetime.timedelta(days=1)
   last_sunday = last_sunday.replace(
       hour=0, minute=0, second=0, microsecond=0)  

   return last_sunday


HourSpan = collections.namedtuple('HourSpan', [
  'start_hr',  # 0 - 23 inclusive.
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
      json.loads(urlfetch.fetch(
        'https://luci-config.appspot.com/_ah/api/config/v1/config_sets/'
        'projects%2Fchromium%2Frefs%2Fheads%2Fmaster/config/cq.cfg'
      ).content)['content'])

  config = cq_pb2.Config()
  text_format.Merge(cq_config, config)

  builders = []
  if config.verifiers.HasField('try_job'):
    for bucket in config.verifiers.try_job.buckets:
      for builder in bucket.builders:
        if not builder.HasField('experiment_percentage'):
          builders.append(builder.name)
  return builders


def fields_to_dicts(query_response):
  fields = [
      field['name'] for field in query_response['schema']['fields']]
  rows = []
  for row in query_response['rows']:
    row_dict = {}
    for field, f in zip(fields, row['f']):
      row_dict[field] = f['v']
    rows.append(row_dict)
  return rows


def execute_percentile_query(
    bigquery_service, table, builders, dates):
  QUERY = """
    SELECT builder, 
        CASE
        {% for date in dates %}
          WHEN build_sched_msec >= {{ '%f' % date[0] }}
                AND build_sched_msec < {{ '%f' % date[1] }}
          THEN {{ loop.index - 1}}
        {% endfor %}
        END as day_index,
        ROW_NUMBER() OVER (
            PARTITION BY builder, day_index ORDER BY
            total_execution_minutes) as pre_percentile,
        quantiles(total_duration_s, 101) / 60.0 as total_execution_minutes
    FROM (
      SELECT builder, build_sched_msec, total_duration_s
      FROM {{ table }}
      WHERE
          (
          {% for date in dates %}
            (build_sched_msec >= {{ '%f' % date[0] }} AND
              build_sched_msec < {{ '%f' % date[1] }})
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
      GROUP BY builder, day_index
  """

  try:
      query_request = bigquery_service.jobs()
      query_data = {
          'query': Environment().from_string(QUERY).render(
            dates=dates,
            builders=builders,
            table=table)
      }

      # print query_data['query']

      query_response = query_request.query(
          projectId=GAE_APP_ID,
          body=query_data).execute()

      results = collections.defaultdict(lambda: collections.defaultdict(dict))
      rows = fields_to_dicts(query_response)
      for row_dict in rows:
        percentile = int(row_dict['pre_percentile']) - 1  # 1-based in BQ.
        execution_time = float(row_dict['total_execution_minutes'])
        results[
            row_dict['builder']][
                int(row_dict['day_index'])][
                  percentile] = execution_time

      return results

  except HttpError as err:
      # print('Error: {}'.format(err.content))
      raise err


def verify_slo_spec(slo_spec):
  assert len(slo_spec) == 7


def verify_slo_bounds(slo_bounds):
  for percentile in slo_bounds:
    assert percentile >= 0
    assert percentile <= 100

def identify_violations(timing_data, slo_bounds, dates):
  violation_list = []
  for buildername, builder_days in timing_data.iteritems():
    for day_index, builder_percentiles in builder_days.iteritems():
      start, end = dates[day_index]
      for percentile, bound in slo_bounds.iteritems():
        # Reduce to ints to eliminate subsecond inaccuracies.
        if int(builder_percentiles[percentile]) > int(bound):
          violation_list.append({
            'builder': buildername,
            'start': start,
            'end': end,
            'percentile': percentile,
            'slo': bound * 60.0,
            'actual': builder_percentiles[percentile] * 60.0,
          })
  return violation_list


def get_violation_links(
    bigquery_service, table, violations, dates):
  QUERY = """
    SELECT master, builder, build_number, 
    CASE
    {% for violation in violations %}
      WHEN  builder = '{{ violation['builder'] }}'
            AND build_sched_msec >= {{ '%f' % violation['start'] }}
            AND build_sched_msec < {{ '%f' % violation['end'] }}
            AND total_duration_s >= {{ '%f' % violation['slo'] }}
            {% if violation['percentile'] != 100 %}
            AND total_duration_s < {{ '%f' % violation['actual'] }}
            {% endif %}
      THEN {{ loop.index - 1}}
    {% endfor %}
    END as violation_index,
    build_sched_msec
    FROM {{ table }}
    WHERE
      {% for violation in violations %}
        (
            builder = '{{ violation['builder'] }}'
            AND build_sched_msec >= {{ '%f' % violation['start'] }}
            AND build_sched_msec < {{ '%f' % violation['end'] }}
            AND total_duration_s >= {{ '%f' % violation['slo'] }}
            {% if violation['percentile'] != 100 %}
            AND total_duration_s < {{ '%f' % violation['actual'] }}
            {% endif %}
        )
        {% if not loop.last %}
        OR
        {% endif %}
      {% endfor %}
  """ 
  try:
      query_request = bigquery_service.jobs()
      query_data = {
          'query': Environment().from_string(QUERY).render(
            violations=violations,
            table=table)
      }

      # print query_data['query']

      query_response = query_request.query(
          projectId=GAE_APP_ID,
          body=query_data).execute()
      results = [[] for _ in range(len(violations))]
      for row_dict in fields_to_dicts(query_response):
        # Remove 'master.'
        row_dict['master'] = row_dict['master'][len('master.'):]
        template = ('https://build.chromium.org/p/'
            '%(master)s/builders/%(builder)s/builds/%(build_number)s')
        idx = int(row_dict['violation_index'])
        results[idx].append(template % row_dict)
      return results


  except HttpError as err:
      # print('Error: {}'.format(err.content))
      raise err


def collate_violations(violations, violation_links):
  collated_violations = collections.defaultdict(
      lambda: collections.defaultdict(
        lambda: collections.defaultdict(list)))
  for violation, links in zip(violations, violation_links):
    strdate = datetime.datetime.utcfromtimestamp(
        violation['start'] / 1000.0).strftime('%Y-%m-%d')

    collated_violations[
        strdate][
            violation['builder']][
                violation['percentile']] = {
                  'slo': violation['slo'],
                  'actual': violation['actual'],
                  'builds': sorted(links),
                }

  return collated_violations


def slo_score(slo_bounds, builders, collated_violations, dates):
    daily_scores = []
    daily_slo_num = len(slo_bounds) * len(builders)
    for strdate, daily_violations in collated_violations.iteritems():
      num_violations = sum(
          len(percentiles) for percentiles in daily_violations.itervalues())
      daily_scores.append({
          'date': strdate,
          'percentage': 100.0 * (
            daily_slo_num - num_violations) / float(daily_slo_num),
          'met': daily_slo_num - num_violations,
          'total': daily_slo_num,
      })

    total_slo_num = len(dates) * daily_slo_num
    total_violations = sum(
        sum(len(percentiles) for percentiles in daily_violations.itervalues())
        for daily_violations in collated_violations.itervalues())

    return daily_scores, {
        'percentage': 100.0 * (
          total_slo_num - total_violations) / float(total_slo_num),
        'met': total_slo_num - total_violations,
        'total': total_slo_num,
    }

def main():
    table = models.BigQueryTable.get_or_insert('table_name').table
    print table
    slo_spec = [
        None,  # Sunday.
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        HourSpan(10, 'Europe/Berlin', 18, 'America/Los_Angeles'),
        None,  # Saturday.
    ]

    slo_bounds = {
        50: 45.0,  # Percentile: minutes.
        90: 90.0,
        100: 120.0,
    }

    verify_slo_spec(slo_spec)
    verify_slo_bounds(slo_bounds)

    builders = get_builders()
    dates = slo_one_week(last_sunday() - datetime.timedelta(days=7), slo_spec)

    week_of = datetime.datetime.utcfromtimestamp(
        dates[0][0] / 1000.0).strftime('%Y-%m-%d')

    # Grab the application's default credentials from the environment.
    credentials = GoogleCredentials.get_application_default()
    # Construct the service object for interacting with the BigQuery API.
    bigquery_service = build('bigquery', 'v2', credentials=credentials)

    percentiles = execute_percentile_query(
        bigquery_service, table, builders, dates)

    violations = identify_violations(percentiles, slo_bounds, dates)

    violation_links = get_violation_links(bigquery_service, table, violations, dates)

    collated_violations = collate_violations(violations, violation_links)

    daily_scores, total_score = slo_score(
        slo_bounds, builders, collated_violations, dates)

    return week_of, collated_violations, daily_scores, total_score
