CREATE TABLE data (
  key varchar(40) UNIQUE,
  jobs integer,
  builder varchar(30),
  target varchar(30),
  cpu integer,
  ram float,
  disk integer,
  instance varchar(20),
  run integer,
  iter integer DEFAULT 1,
  time float
);
