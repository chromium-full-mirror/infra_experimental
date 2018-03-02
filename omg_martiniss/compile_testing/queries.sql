SELECT jobs, target, cpu, ram, COUNT(*), AVG(time) FROM data WHERE target = 'all' GROUP BY jobs, target, cpu, ram;
SELECT jobs, target, cpu, ram, COUNT(*), AVG(time) FROM data GROUP BY jobs, target, cpu, ram;
