package cq_analyze

import (
	"crypto/sha256"
	"encoding/json"
	"fmt"
	"net/http"
	"reflect"
	"strconv"
	"strings"
	"time"

	"go.chromium.org/gae/service/memcache"
	"go.chromium.org/luci/common/logging"
	"go.chromium.org/luci/server/auth"
	"golang.org/x/net/context"
	bigquery "google.golang.org/api/bigquery/v2"
)

func hardQueryPrefix(start, end time.Time) string {
	return fmt.Sprintf(`
WITH
  CQA AS (
    SELECT
      *
    FROM
     `+"`plx.google.chrome_infra.cq_attempts.all`"+`
    WHERE
      attempt_start_msec > %[1]v
      AND attempt_start_msec < %[2]v ),
  CBA AS (
    SELECT
      *
    FROM
      plx.google.chrome_infra.completed_builds.all
    WHERE
      build_sched_msec > %[1]v
      AND build_sched_msec < %[2]v ),
  CSA AS (
    SELECT
      *
    FROM
      plx.google.chrome_infra.completed_steps.all
    WHERE
      build_sched_msec > %[1]v
      AND build_sched_msec < %[2]v ),
  unnested AS (
    SELECT
      A.attempt_start_msec,
      A.patchset,
      A.issue,
      (A.click_to_patch_committed_sec > 0) AS committed,
      id
    FROM
      CQA AS A
    CROSS JOIN
      UNNEST(A.contributing_bbucket_ids) AS id
    WHERE
      A.cq_name = 'chromium/chromium/src'),
  builds_with_patch_url AS (
    SELECT
      master,
      builder,
      build_sched_msec,
      execution_duration_s,
      SPLIT(patch_url, "/") AS parts
    FROM
      CBA
    WHERE
      patch_url IS NOT NULL
      AND LENGTH(patch_url) > 6
      AND STRPOS(patch_url, "codereview") = 0 ),
  chromium_tryjob_builds AS (
    SELECT
      A.master,
      A.builder,
      A.build_sched_msec,
      A.execution_duration_s,
      parts[OFFSET(7)] AS issue,
      parts[OFFSET(8)] AS patchset
    FROM
      builds_with_patch_url AS A
    WHERE
      A.builder IN (
        'android_arm64_dbg_recipe',
        'android_clang_dbg_recipe',
        'android_compile_dbg',
        'android_cronet',
        'android_n5x_swarming_rel',
        'cast_shell_android',
        'linux_android_rel_ng',
        'cast_shell_linux',
        'chromeos_amd64-generic_chromium_compile_only_ng',
        'chromeos_daisy_chromium_compile_only_ng',
        'chromium_presubmit',
        'fuchsia_arm64',
        'fuchsia_compile',
        'fuchsia_x64',
        'linux_chromium_asan_rel_ng',
        'linux_chromium_chromeos_rel_ng',
        'linux_chromium_compile_dbg_ng',
        'linux_chromium_headless_rel',
        'linux_chromium_rel_ng',
        'linux_chromium_tsan_rel_ng',
        'ios-simulator',
        'mac_chromium_compile_dbg_ng',
        'mac_chromium_rel_ng',
        'win-msvc-rel',
        'win10_chromium_x64_rel_ng',
        'win7_chromium_rel_ng',
        'win_chromium_compile_dbg_ng',
        'win_chromium_rel_ng',
        'win_clang')
      AND parts[OFFSET(4)] = "chromium"
      AND parts[OFFSET(5)] = "src"
      AND parts[OFFSET(6)] = "+" ),
  total_time_per_builder AS (
    SELECT
      issue,
      patchset,
      master,
      builder,
      SUM(execution_duration_s) AS total_time
    FROM
      chromium_tryjob_builds
    GROUP BY
      issue,
      patchset,
      master,
      builder ),
  data AS (
    SELECT
      attempt_start_msec,
      issue,
      patchset,
      click_to_result_sec / 60 AS CTR_min,
      click_to_patch_committed_sec / 60 AS CTC_min,
      first_start_msec,
      fail_type
    FROM
      CQA
    WHERE
      cq_name = 'chromium/chromium/src'
      AND (fail_type IS NULL
        OR fail_type NOT IN (
          8, /* MANUAL_CANCEL */
          5, /* MISSING_LGTM*/
          4, /* NOT_LGTM */
          1, /* FAILED_PRESUBMIT_BOT */
          17, /*FAILED_PRESUBMIT_BOT_INFRA */
          12, /* FAILED_REMOTE_REF_PRESUBMIT */
          5, /* COMMIT_FALSE */
          10, /* OPEN_DEPENDENCY */
          6, /*NO_SIGNCLA */
          14, /*FAILED_COMMIT */
          2 /*FAILED_JOBS */ )) ),
  id_parent_tup AS (
    SELECT
      A.issue,
      B.patchset,
      A.attempt_start_msec,
      A.id
    FROM (
      SELECT
        issue,
        MIN(attempt_start_msec) AS attempt_start_msec,
        id
      FROM
        unnested
      GROUP BY
        issue,
        id) AS A
    INNER JOIN
      CQA AS B
    ON
      A.issue = B.issue
      AND A.attempt_start_msec = B.attempt_start_msec ),
  tup_has_compile AS (
    SELECT
      A.issue,
      A.patchset,
      A.attempt_start_msec,
      A.id
    FROM
      unnested AS A
    INNER JOIN
     CSA AS B
    ON
      A.id = B.bbucket_id
    WHERE
      STRPOS(B.step_name, 'compile') = 1
    GROUP BY
      A.issue,
      A.patchset,
      A.attempt_start_msec,
      A.id ),
  tup_has_compile_no_child AS (
    SELECT
      A.issue,
      A.attempt_start_msec,
      A.patchset
    FROM
      id_parent_tup AS A
    INNER JOIN
      tup_has_compile AS B
    ON
      A.issue = B.issue
      AND A.attempt_start_msec = B.attempt_start_msec
      AND A.patchset = B.patchset
    GROUP BY
      A.issue,
      A.attempt_start_msec,
      A.patchset ),
  data_has_compile AS (
    SELECT
      C.issue,
      C.patchset,
      C.attempt_start_msec,
      D.CTR_min,
      D.CTC_min
    FROM
      tup_has_compile_no_child AS C
    INNER JOIN
      data AS D
    ON
      C.issue = D.issue
      AND C.patchset = D.patchset
      AND C.attempt_start_msec = D.attempt_start_msec ),
  time_from_builds AS (
    SELECT
      A.issue,
      A.patchset,
      A.attempt_start_msec,
      MAX(total_time) AS longest_time
    FROM
      id_parent_tup AS A
    INNER JOIN
      total_time_per_builder AS B
    ON
      A.issue = B.issue
      AND A.patchset = B.patchset
    GROUP BY
      A.issue,
      A.patchset,
      A.attempt_start_msec ),
  tmp AS (
    SELECT
      A.issue,
      A.patchset,
      A.attempt_start_msec,
      B.master,
      B.builder,
      B.total_time
    FROM
      time_from_builds AS A
    INNER JOIN
      total_time_per_builder AS B
    ON
      A.issue = B.issue
      AND A.patchset = B.patchset
      AND A.longest_time = B.total_time ),
  only_valid AS (
    SELECT
      A.*,
      TIMESTAMP_TRUNC(TIMESTAMP_MILLIS(CAST(A.attempt_start_msec AS INT64)), DAY) AS day_ts
    FROM
      tmp AS A
    INNER JOIN
      data_has_compile AS B
    ON
      A.issue = B.issue
      AND A.patchset = B.patchset
      AND A.attempt_start_msec = B.attempt_start_msec )
`, start.UTC().Unix()*1000, end.UTC().Unix()*1000) // attempt_start_msec is in milliseconds.
}

// Gets a table of number of times a builder was the slowest builder for an issue/patchset pair
func limitingQuery(start, end time.Time) string {
	return hardQueryPrefix(start, end) + `,grouped AS (
    SELECT
      builder,
      COUNT(*) AS count,
      AVG(total_time) AS avg_time,
      APPROX_QUANTILES(total_time, 100)[OFFSET(90)] AS ninety_time,
      APPROX_QUANTILES(total_time, 100)[OFFSET(95)] AS ninety_five_time
    FROM
      only_valid
    GROUP BY
      builder )
SELECT
  *
FROM
  grouped
ORDER BY
  count DESC
LIMIT
  50
`
}

// Gets a table of number of times a builder was the slowest builder for an issue/patchset pair
func longestBuilds(builder string, start, end time.Time) string {
	return hardQueryPrefix(start, end) + fmt.Sprintf(`
  SELECT builder, issue, patchset, attempt_start_msec AS attempt_start, total_time AS duration
  FROM only_valid
  WHERE builder = '%s' AND total_time > 2 * 60 * 60
  GROUP BY builder, issue, patchset, attempt_start_msec, total_time
  ORDER BY total_time DESC
`, builder)
}

// Gets all builds for a builder
func buildsQuery(builder string, start, end time.Time) string {
	return fmt.Sprintf(`
  SELECT
    master,
    build_number,
    build_sched_msec AS build_sched,
    execution_duration_s AS duration,
    result
  FROM plx.google.chrome_infra.completed_builds.all
  WHERE
    builder = '%s'
    AND build_sched_msec > %v
    AND build_sched_msec < %v
  ORDER BY
    execution_duration_s DESC
`, builder, start.UTC().Unix()*1000, end.UTC().Unix()*1000)
}

// Gets all builds for a builder
func longStepsQuery(builder string, start, end time.Time) string {
	return fmt.Sprintf(`
WITH dat AS (
  SELECT
    step_name, APPROX_QUANTILES(step_duration_s, 100) AS quant
  FROM plx.google.chrome_infra.completed_steps.all
  WHERE
    builder = '%v'
    AND build_sched_msec > %v
    AND build_sched_msec < %v
  GROUP BY step_name
)
SELECT step_name AS name, quant[OFFSET(50)] as duration_avg, quant[OFFSET(90)] AS duration_90
FROM dat
ORDER BY quant[OFFSET(50)] DESC
`, builder, start.UTC().Unix()*1000, end.UTC().Unix()*1000)
}

// Gets a table of number of times a builder was the slowest builder for an issue/patchset pair
func clInfoQuery(builder, issue, patchset string) string {
	return fmt.Sprintf(`
WITH builds_with_patch_url AS (
    SELECT
      master,
      builder,
      build_number,
      build_sched_msec,
      result,
      execution_duration_s,
      SPLIT(patch_url, "/") AS parts
    FROM
      plx.google.chrome_infra.completed_builds.all
    WHERE
      builder = '%s'
      AND patch_url IS NOT NULL
      AND LENGTH(patch_url) > 6
      AND STRPOS(patch_url, "codereview") = 0 )
  SELECT
    master,
    build_number,
    build_sched_msec AS build_sched,
    result,
    execution_duration_s as duration
  FROM
    builds_with_patch_url
  WHERE
    parts[OFFSET(4)] = "chromium"
    AND parts[OFFSET(5)] = "src"
    AND parts[OFFSET(6)] = "+"
    AND parts[OFFSET(7)] = "%s"
    AND parts[OFFSET(8)] = "%s"
  ORDER BY
    build_number DESC
	`, builder, issue, patchset)
}

func buildInfoQuery(builder string, buildNumber int64) string {
	return fmt.Sprintf(`
    SELECT step_name AS name, master, step_duration_s AS duration, step_number AS number, result
    FROM plx.google.chrome_infra.completed_steps.all
    WHERE builder = '%s' AND build_number = %v
    ORDER BY step_number
    ;
`, builder, buildNumber)
}

func knownBuildersQuery(start, end time.Time) string {
	return fmt.Sprintf(`
WITH
  unnested AS (
    SELECT
     attempt_start_msec,
		 patchset,
		 issue,
		 (click_to_patch_committed_sec > 0) AS committed,
		 id
	FROM
		plx.google.chrome_infra.cq_attempts.all
  CROSS JOIN
		UNNEST(contributing_bbucket_ids) AS id
  WHERE
		cq_name = 'chromium/chromium/src'
		AND attempt_start_msec > %v
		AND attempt_start_msec < %v
   ),
  cq_builders AS (
    SELECT master, builder, COUNT(*) AS num_builds
    FROM unnested AS A
		INNER JOIN
			plx.google.chrome_infra.completed_builds.all AS B
      ON A.id = B.bbucket_id
    GROUP BY master, builder
    ),
  main_cq_builders AS (
    SELECT master, builder
    FROM cq_builders
    WHERE num_builds > 2000
    ORDER BY master, builder
  )
  SELECT *
  FROM main_cq_builders
`, start.UTC().Unix()*1000, end.UTC().Unix()*1000)
}

func fetchQuery(c context.Context, query string, cacheTime time.Duration) (*bigquery.GetQueryResultsResponse, error) {
	h := sha256.New()
	h.Write([]byte(query))
	itm := memcache.NewItem(c, fmt.Sprintf("query|%x", h.Sum(nil)))
	if cacheTime > 0 {
		itm.SetExpiration(cacheTime)
	}
	logging.Debugf(c, "caching query for %d minutes", cacheTime/time.Minute)
	finalRes := &bigquery.GetQueryResultsResponse{}
	if err := memcache.Get(c, itm); err != nil {
		if err != memcache.ErrCacheMiss {
			logging.Warningf(c, "got error while reading query result from memcache: %v", err)
		}
		c, cancel := context.WithTimeout(c, 10*time.Minute)
		defer cancel()
		tr, err := auth.GetRPCTransport(c, auth.AsSelf, auth.WithScopes(bigquery.BigqueryScope))
		if err != nil {
			panic(err)
		}
		s, err := bigquery.New(&http.Client{
			Transport: tr,
			Timeout:   10 * time.Minute,
		})
		if err != nil {
			panic(err)
		}
		b := false
		q := s.Jobs.Query("chrome-infra-events", &bigquery.QueryRequest{
			Query:        query,
			UseLegacySql: &b,
			TimeoutMs:    3000, // Very low timeout, because we request the results later.
		})
		res, err := q.Do()
		if err != nil {
			panic(err)
		}
		logging.Infof(c, "running job %v %v res %v", res.JobReference.ProjectId, res.JobReference.JobId, res.JobComplete)

		finalRes = &bigquery.GetQueryResultsResponse{
			JobComplete: res.JobComplete,
			Rows:        res.Rows,
			Schema:      res.Schema,
		}
		for !finalRes.JobComplete {
			logging.Infof(c, "polling for results for %v", res.JobReference.JobId)
			resultsCall := s.Jobs.GetQueryResults(res.JobReference.ProjectId, res.JobReference.JobId)

			finalRes, err = resultsCall.Do()
			if err != nil {
				panic(err)
			}
		}
		jsonData, err := json.Marshal(finalRes)
		if err != nil {
			logging.Warningf(c, "while trying to json.Marshal query results: %v", err)
		}
		itm.SetValue(jsonData)
		if err := memcache.Set(c, itm); err != nil {
			return nil, fmt.Errorf("error while writing result to memcache: %v", err)
		}
	}
	if len(finalRes.Rows) == 0 {
		if len(itm.Value()) == 0 {
			logging.Warningf(c, "query completed but no results")
			return finalRes, nil
		}
		logging.Infof(c, "query cache hit")
		if err := json.Unmarshal(itm.Value(), finalRes); err != nil {
			return nil, fmt.Errorf("error while reading result from memcache: %v", err)
		}
	}
	return finalRes, nil
}

func runQuery(c context.Context, query string, result interface{}, cacheTime time.Duration) error {
	if !reflect.ValueOf(result).Elem().CanSet() {
		return fmt.Errorf("result must be settable (a pointer)")
	}
	t := reflect.TypeOf(result).Elem()
	if t.Kind() != reflect.Slice {
		return fmt.Errorf("result must be a slice, is %v", t)
	}
	elemT := t.Elem()
	if elemT.Kind() != reflect.Ptr {
		return fmt.Errorf("result slice elements must be a pointers, is %v", t.Elem())
	}
	elemT = elemT.Elem()
	fieldToBQName := map[string]string{}
	for i := 0; i < elemT.NumField(); i++ {
		f := elemT.Field(i)
		tag := f.Tag.Get("json")
		if tag == "" {
			continue
		}
		if strings.Contains(tag, ",") {
			tag = strings.Split(tag, ",")[0]
		}

		fieldToBQName[tag] = f.Name
	}

	res, err := fetchQuery(c, query, cacheTime)
	if err != nil {
		panic(err)
	}

	zV := reflect.Value{}
	resultSlice := reflect.MakeSlice(t, len(res.Rows), len(res.Rows))
	for i, row := range res.Rows {
		itm := resultSlice.Index(i)
		madeItm := reflect.New(elemT)
		itm.Set(madeItm)
		for fieldNum, cell := range row.F {
			schema := res.Schema.Fields[fieldNum]
			value := reflect.ValueOf(cell.V)
			asS := cell.V.(string)
			switch schema.Type {
			case "INTEGER":
				res, err := strconv.Atoi(asS)
				if err != nil {
					panic(err)
				}
				value = reflect.ValueOf(int32(res))
			case "INT64":
				res, err := strconv.Atoi(asS)
				if err != nil {
					panic(err)
				}
				value = reflect.ValueOf(int64(res))
			case "FLOAT":
				res, err := strconv.ParseFloat(asS, 64)
				if err != nil {
					panic(err)
				}
				value = reflect.ValueOf(res)
			case "TIMESTAMP":
				err := fmt.Errorf("i don't like timestamps, convert them in big query to ints instead pls")
				logging.Errorf(c, err.Error())
				return err
			case "STRING":
			default:
				err := fmt.Errorf("unknown field type '%s'", schema.Type)
				logging.Errorf(c, err.Error())
				return err
			}
			field := madeItm.Elem().FieldByName(fieldToBQName[schema.Name])
			//logging.Debugf(c, "got field %v for %v:%v (type %v)", field, schema.Name, value, schema.Type)
			if field != zV {
				field.Set(value)
			}
		}
	}
	reflect.ValueOf(result).Elem().Set(resultSlice)
	return nil
}
