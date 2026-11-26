#!/bin/sh
set -eu

if /opt/hive/bin/schematool -dbType postgres -info >/tmp/schema-info.log 2>&1; then
  exit 0
fi

/opt/hive/bin/schematool -dbType postgres -initSchema --verbose
