CREATE DATABASE cs_tools;
USE cs_tools;


CREATE TABLE alert (
      at   DATETIME
    , type VARCHAR(255)
    , msg  VARCHAR(255)
);

ALTER TABLE cs_tools.alert ADD CONSTRAINT PRIMARY KEY (at, type, msg);


CREATE TABLE event (
      at      DATETIME
    , user    VARCHAR(255)
    , summary VARCHAR(255)
);

ALTER TABLE cs_tools.event ADD CONSTRAINT PRIMARY KEY (at, user, summary);


CREATE TABLE table_info (
      database_name     VARCHAR(255)
    , schema_name       VARCHAR(255)
    , table_name        VARCHAR(255)
    , table_guid        VARCHAR(255)
    , state             VARCHAR(255)
    , database_version  BIGINT
    , serving_version   BIGINT
    , building_version  BIGINT
    , build_duration    BIGINT
    , last_build_time   BIGINT
    , is_known          BOOL
    , database_status   VARCHAR(255)
    , last_uploaded_at  DATETIME
    , num_of_rows       BIGINT
    , approx_bytes_size BIGINT
    , uncompressed_bytes_size BIGINT
    , row_skew          BIGINT
    , num_shards        BIGINT
    , csv_size_with_replication_mb DOUBLE
    , replicated        BOOL
    , ip                VARCHAR(255)
);

ALTER TABLE cs_tools.table_info ADD CONSTRAINT PRIMARY KEY (table_guid, ip);
