CREATE DATABASE "TS_Performance_Analysis";

USE "TS_Performance_Analysis";

CREATE TABLE "TS_Table_Analysis" (
  "Database Name" VARCHAR(0),
  "Schema Name" VARCHAR(0),
  "Table Name" VARCHAR(0),
  "Table Guid" VARCHAR(0),
  "Status" VARCHAR(0),
  "Serving Timestamp" VARCHAR(0),
  "Total Row Count" INT64,
  "Row Count Skew" INT,
  "Uncompressed Size (MB)" DOUBLE,
  "Estimated Size (MB)" DOUBLE,
  "Estimated Size (MB) Skew" DOUBLE,
  "Total Shards" INT,
  "Cluster Space Used (MB)" DOUBLE,
  "Last Updated Timestamp" VARCHAR(0),
  "Deleted Rows" INT,
 PRIMARY KEY ("Table Guid" )
);

