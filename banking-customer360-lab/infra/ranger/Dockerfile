FROM maven:3.9.9-eclipse-temurin-11 AS build

ARG RANGER_VERSION=2.6.0
ENV MAVEN_OPTS="-Xms1g -Xmx2g"

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl python3 build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo.huaweicloud.com/apache/ranger/${RANGER_VERSION}/apache-ranger-${RANGER_VERSION}.tar.gz" -o /tmp/ranger.tar.gz \
    && echo "2c25efe823f9c4c9501bebe9468e0e1cbe8f67922426c6862c8b14a5da278aa55b92be146e8a26fe31a9c47b95d7529f609d9fb7bf5b655942c9233b0b7a2548  /tmp/ranger.tar.gz" | sha512sum -c - \
    && mkdir /src \
    && tar -xzf /tmp/ranger.tar.gz --strip-components=1 -C /src \
    && rm /tmp/ranger.tar.gz

RUN --mount=type=cache,target=/root/.m2 \
    cd /src \
    && mvn -q -P='ranger-admin,!linux' -Dmaven.test.skip=true -DskipJSTests=true -Denunciate.skip=true clean package \
    && test -f "target/ranger-${RANGER_VERSION}-admin.tar.gz"

FROM eclipse-temurin:8-jre-jammy

ARG RANGER_VERSION=2.6.0
ARG POSTGRES_JDBC_VERSION=42.7.4

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gettext-base gosu netcat-openbsd procps python3 python3-requests \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 ranger \
    && useradd --uid 1000 --gid 1000 --home-dir /home/ranger --create-home --shell /bin/bash ranger \
    && mkdir -p /opt/ranger /var/log/ranger /var/run/ranger /usr/share/java \
    && curl -fsSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar" -o /usr/share/java/postgresql.jar

COPY --from=build /src/target/ranger-${RANGER_VERSION}-admin.tar.gz /tmp/ranger-admin.tar.gz
RUN tar -xzf /tmp/ranger-admin.tar.gz -C /opt/ranger \
    && ln -s "/opt/ranger/ranger-${RANGER_VERSION}-admin" /opt/ranger/admin \
    && rm /tmp/ranger-admin.tar.gz \
    && chown -R ranger:ranger /opt/ranger /var/log/ranger /var/run/ranger

COPY ranger/config/install.properties.template /opt/customer360/install.properties.template
COPY ranger/entrypoint.sh /opt/customer360/entrypoint.sh
RUN chmod 0555 /opt/customer360/entrypoint.sh

ENV RANGER_HOME=/opt/ranger
ENV RANGER_ADMIN_HOME=/opt/ranger/admin
EXPOSE 6080
ENTRYPOINT ["/opt/customer360/entrypoint.sh"]
