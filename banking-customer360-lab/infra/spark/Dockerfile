FROM maven:3.9.9-eclipse-temurin-17 AS dependencies

ARG DELTA_VERSION=3.2.0
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_BUNDLE_VERSION=1.12.262
ARG POSTGRES_JDBC_VERSION=42.7.4
ARG MYSQL_JDBC_VERSION=8.4.0

COPY infra/spark/dependencies/pom.xml /tmp/hive-pom.xml
RUN mkdir -p /runtime-jars /hive-metastore-jars \
    && mvn -q -f /tmp/hive-pom.xml dependency:copy-dependencies -DoutputDirectory=/hive-metastore-jars \
    && curl -fsSL "https://repo1.maven.org/maven2/io/delta/delta-spark_2.12/${DELTA_VERSION}/delta-spark_2.12-${DELTA_VERSION}.jar" -o "/runtime-jars/delta-spark_2.12-${DELTA_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/io/delta/delta-storage/${DELTA_VERSION}/delta-storage-${DELTA_VERSION}.jar" -o "/runtime-jars/delta-storage-${DELTA_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" -o "/runtime-jars/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE_VERSION}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar" -o "/runtime-jars/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar" -o "/runtime-jars/postgresql-${POSTGRES_JDBC_VERSION}.jar" \
    && curl -fsSL "https://repo1.maven.org/maven2/com/mysql/mysql-connector-j/${MYSQL_JDBC_VERSION}/mysql-connector-j-${MYSQL_JDBC_VERSION}.jar" -o "/runtime-jars/mysql-connector-j-${MYSQL_JDBC_VERSION}.jar"

FROM eclipse-temurin:17-jre-jammy

ARG SPARK_VERSION=3.5.6
ARG DELTA_VERSION=3.2.0

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl python3 python3-pip tini procps \
    && rm -rf /var/lib/apt/lists/* \
    && curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo.huaweicloud.com/apache/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop3.tgz" -o /tmp/spark.tgz \
    && echo "1b9ce1cd6e1b78d08f5f36a0b2b9b6802c1e22a20c6b0c6f53ef56bb352ad1b5812e0de7927cb0d2eadcca17cfaa701d6ee0b8ebf8f0689e80a36679e15cd3a3  /tmp/spark.tgz" | sha512sum -c - \
    && tar -xzf /tmp/spark.tgz -C /opt \
    && mv "/opt/spark-${SPARK_VERSION}-bin-hadoop3" /opt/spark \
    && rm /tmp/spark.tgz \
    && python3 -m pip install --no-cache-dir --no-deps "delta-spark==${DELTA_VERSION}" \
    && python3 -m pip install --no-cache-dir "boto3==1.35.99" "requests==2.32.3" "PyYAML==6.0.2"

COPY --from=dependencies /runtime-jars/ /opt/spark/jars/
COPY --from=dependencies /hive-metastore-jars/ /opt/spark/hive-metastore-jars/
COPY infra/spark/conf/spark-defaults.conf /opt/spark/conf/spark-defaults.conf
COPY infra/spark/conf/hive-site.xml /opt/spark/conf/hive-site.xml
COPY infra/spark/submit-wrapper.sh /usr/local/bin/spark-submit

RUN chmod 0555 /usr/local/bin/spark-submit \
    && groupadd --gid 185 spark \
    && useradd --uid 185 --gid 185 --home-dir /home/spark --create-home --shell /bin/bash spark \
    && mkdir -p /spark-events /opt/spark/jobs \
    && chown -R spark:spark /spark-events /opt/spark /home/spark

ENV SPARK_HOME=/opt/spark
ENV PATH=/usr/local/bin:/opt/spark/bin:${PATH}
ENV PYSPARK_PYTHON=python3
ENV SPARK_NO_DAEMONIZE=true

USER spark
WORKDIR /opt/spark/work-dir
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["spark-submit", "--version"]
