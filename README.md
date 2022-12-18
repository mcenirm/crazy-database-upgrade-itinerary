# Overview

Summary: Need to upgrade several databases from version Postgresql 9.4 with Postgis 2.1 to version Postgresql 15 with Postgis 3.3.

https://postgis.net/workshops/postgis-intro/upgrades.html says to:

* Upgrade Postgresql but use the same version of Postgis (eg, using `pg_upgrade`, or `pg_dumpall` + `psql`)
* Upgrade Postgis
  * Stop Postgresql
  * Replace Postgis software
  * Start Postgresql
  * Update/upgrade Postgis extensions in each database
    * Before Postgis 2.5: `ALTER EXTENSION postgis UPDATE;` (TODO: Is `... UPDATE TO '<SPECIFIC VERSION>';` necessary?)
    * Postgis 2.5 or later: `SELECT postgis_extensions_upgrade();`

The planned approach is to leverage [containers based on CentOS 7](https://hub.docker.com/_/centos/)
and the packages from [PGDG](https://yum.postgresql.org/) to implement the upgrades,
since that's the only OS release for which PGDG covers all Postgis versions.

* **Input**: The starting dump using `pg_dumpall` from the Postgresql 9.4 with Postgis 2.1 cluster
* **Output**: A final dump using `pg_dumpall` from the Postgresql 15 with Postgis 3.3 cluster


| Step |     Postgresql    |      Postgis      |
|:----:|:-----------------:|:-----------------:|
|   0  |           9.4     |         2.1       |
|   1  |           9.4     | Update to **2.4** |
|   2  | Upgrade to **11** |         2.4       |
|   3  |          11       | Update to **3.3** |
|   4  | Upgrade to **15** |         3.3       |


Glaring flaw / TODO: Regression tests for the actual application.


# Components

## Images

Assumption: Images will be local-only.

* `base:el7` - PGDG repos enabled
  * `postgis:21_94` - Postgresql 9.4 and Postgis 2.1
  * `postgis:24_94` - Postgresql 9.4 and Postgis 2.4
  * `postgis:24_11` - Postgresql 11 and Postgis 2.4
  * `postgis:33_11` - Postgresql 11 and Postgis 3.3
  * `postgis:33_15` - Postgresql 15 and Postgis 3.3

## Container volumes (`compose.yml`)

* `pgdata94` - Named volume for Postgresql 9.4
* `pgdata11` - Named volume for Postgresql 11
* `pgdata15` - Named volume for Postgresql 15

## Services (`compose.yml`)

* `postgis_XX_YY_db` - Runs Postgresql under systemd
* `postgis_XX_YY` - CLI version


# Step 0

* Use service `postgis_21_94` to `initdb`
* Launch service `postgis_21_94_db`
* Use service `postgis_21_94` to import dump from `inputdump/TBD.sql`
* Stop serivce `postgis_21_94_db`


# Step 1

* Launch service `postgis_24_94_db`
* Use service `postgis_24_94` to update Postgis in each database
* Use service `postgis_24_94` to `pg_dumpall` to `intermediatedumps/dumpall_24_94.sql`
* Stop serivce `postgis_21_94_db`


# Step 2

* Use service `postgis_24_11` to `initdb`
* Launch service `postgis_24_11_db`
* Use service `postgis_24_11` to import dump from `intermediatedumps/dumpall_24_94.sql`
* Stop serivce `postgis_24_11_db`


# Step 3

* Launch service `postgis_33_11_db`
* Use service `postgis_33_11` to update Postgis in each database
* Use service `postgis_33_11` to `pg_dumpall` to `intermediatedumps/dumpall_33_11.sql`
* Stop serivce `postgis_33_11_db`


# Step 4

* Use service `postgis_33_15` to `initdb`
* Launch service `postgis_33_15_db`
* Use service `postgis_33_15` to import dump from `intermediatedumps/dumpall_33_11.sql`
* Use service `postgis_33_15` to `pg_dumpall` to `intermediatedumps/dumpall_33_15.sql`
* Stop serivce `postgis_33_15_db`
