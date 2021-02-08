CREATE DATABASE cs_tools;
USE cs_tools;


CREATE TABLE user (
      name         VARCHAR(255)
    , display_name VARCHAR(255)
    , email        VARCHAR(255)
    , created      DATETIME
    , modified     DATETIME
);

ALTER TABLE user ADD CONSTRAINT PRIMARY KEY (name);


CREATE TABLE group (
      name         VARCHAR(255)
    , display_name VARCHAR(255)
    , description  VARCHAR(255)
    , created      DATETIME
    , modified     DATETIME
);

ALTER TABLE group ADD CONSTRAINT PRIMARY KEY (name);


CREATE TABLE asso_user_group (
      user_name  VARCHAR(255)
    , group_name VARCHAR(255)
);

ALTER TABLE asso_user_group ADD CONSTRAINT PRIMARY KEY (user_name, group_name);
