#!/bin/sh
set -eu

required="RANGER_DB_NAME RANGER_DB_USER RANGER_DB_PASSWORD RANGER_ADMIN_PASSWORD RANGER_HEAP_SIZE"
for name in $required; do
  eval "value=\${$name:-}"
  if [ -z "$value" ]; then
    echo "Missing required Ranger setting: $name" >&2
    exit 64
  fi
done

envsubst < /opt/customer360/install.properties.template > /opt/ranger/admin/install.properties
chown ranger:ranger /opt/ranger/admin/install.properties
chmod 0600 /opt/ranger/admin/install.properties

if [ ! -f /opt/ranger/.setup-complete ]; then
  gosu ranger sh -c 'cd /opt/ranger/admin && ./setup.sh'
  touch /opt/ranger/.setup-complete
  chown ranger:ranger /opt/ranger/.setup-complete
fi

gosu ranger /opt/ranger/admin/ews/ranger-admin-services.sh start

count=0
while [ "$count" -lt 60 ]; do
  pid=$(ps -ef | awk '/org.apache.ranger.server.tomcat.EmbeddedServer/ && !/awk/ {print $2; exit}')
  if [ -n "$pid" ]; then
    exec tail --pid="$pid" -f /dev/null
  fi
  count=$((count + 1))
  sleep 1
done

echo "Ranger Admin process did not start" >&2
exit 1
