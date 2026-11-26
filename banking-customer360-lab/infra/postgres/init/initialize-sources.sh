#!/bin/sh
set -eu

export CREATE_SOURCE_DATABASES=true
exec /docker-entrypoint-initdb.d/01-databases.sh
