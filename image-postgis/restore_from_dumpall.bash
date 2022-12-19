#!/usr/bin/env bash
set -euo pipefail

[ $# -eq 1 ] || { echo >&2 "Usage: $0 SQLFILE" ; exit 1 ; }

cat -- "$1" \
| sed -r -e '0,/^CREATE DATABASE;/{/^(CREATE ROLE|DROP ROLE( IF EXISTS)?) postgres;/d}' \
| psql -v ON_ERROR_STOP=ON -f -
