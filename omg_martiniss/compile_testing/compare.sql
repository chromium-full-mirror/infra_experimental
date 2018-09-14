SELECT A.jobs, android_count, linux_count, android_avg/linux_avg FROM (
  SELECT jobs, COUNT(*) AS android_count, AVG(time) AS android_avg FROM data WHERE builder="android_n5x_swarming_rel" AND target = "all" AND time > 70 GROUP BY jobs ORDER BY jobs ASC) AS A
  JOIN (
  SELECT jobs, COUNT(*) AS linux_count, AVG(time) AS linux_avg FROM data WHERE builder="linux_chromium_rel_ng" AND target = "all" AND time > 70 GROUP BY jobs ORDER BY jobs ASC) AS B
  ON A.jobs = B.jobs
