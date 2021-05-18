
TQL_HELP = """
Commands can optionally be multi-line.
Few common commands
-----------------------
show databases;       -> list all available databases
use db;               -> switches context to specified database
                         'db' this must be done if queries do
                         not use full names (db.schema.table)
                         for tables.
show schemas;         -> list all schemas within current
                         database (set by use db;)
show tables;          -> list all tables within current
                         database (set by use db;)
show table tab;       -> list all columns for table 'tab'
show views;           -> list all views within current
                         database (set by use db;)
show view vw;         -> list all columns for view 'vw'
script server;        -> generates SQL for all databases
script database db;   -> generates create SQL for all tables in
                         database 'db'
script table tab;     -> generates create SQL for table 'tab'
create database db;   -> create database 'db'
drop database db;     -> drop database 'db'
create table tab ...; -> create table 'tab'. Example ...
                         create table t1 (c1 int, c2 int);
                         create table t2 (d1 int, d2 int,
                         constraint primary key(d1));
drop table tab;       -> drop table 'tab'
alter table tab ...;  -> alter table 'tab'. Examples ...
                         alter table t add column c int
                         default 5;
                         alter table t rename column c to d
                         alter table t drop column c
                         alter table t1 add constraint
                         foreign key (c1, c2) references
                         t2 (d1, d2);
                         alter table t1 drop constraint foreign
                         key t2;
select from tab ...;  -> select query against the specified
                         set of tables. Example queries:
                         select TOP 10 c1 from t1;
                         select c1, sum(c2) from tab1;
                         select c11, sum(c22) as X from t1, t2
                         where t11.c12 = t2.c21 and c13 = 10
                         group by c11
                         order by X desc
                         select c1, sum(c2) from tab1 limit 10;
insert into tab ...;  -> insert values into 'tab'
update tab ...;       -> update rows in 'tbl' that match
                         optionally provided predicates.
                         Predicates are of form column = value
                         connected by 'and' keyword. Set values
                         in 'columns' to specified values.
delete from tab ...;  -> delete rows from 'tbl' that match
                         optionally provided predicates.
                         Predicates are of form column = value
                         connected by 'and' keyword.
compact table tab;    -> compact table 'tab' data version
                         chain to a single DML file.
compact all_tables;   -> compact all tables in current db
exit;                 -> exit.

For a list of all commands, type "help;" after invoking tql

For a list of all available flags, type tql --helpfull
"""
