FROM eclipse-temurin:8-jre-jammy

ARG HIVE_VERSION=3.1.3
ARG POSTGRES_JDBC_VERSION=42.7.4
ARG HADOOP_VERSION=3.1.4
ARG AWS_SDK_BUNDLE_VERSION=1.11.271

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl netcat-openbsd procps \
    && rm -rf /var/lib/apt/lists/* \
    && curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo.huaweicloud.com/apache/hive/hive-${HIVE_VERSION}/apache-hive-${HIVE_VERSION}-bin.tar.gz" -o /tmp/hive.tar.gz \
    && echo "0c9b6a6359a7341b6029cc9347435ee7b379f93846f779d710b13f795b54bb16  /tmp/hive.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/hive.tar.gz -C /opt \
    && mv "/opt/apache-hive-${HIVE_VERSION}-bin" /opt/hive \
    && rm /tmp/hive.tar.gz \
    && curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo1.maven.org/maven2/org/postgresql/postgresql/${POSTGRES_JDBC_VERSION}/postgresql-${POSTGRES_JDBC_VERSION}.jar" -o "/opt/hive/lib/postgresql-${POSTGRES_JDBC_VERSION}.jar" \
    && rm -f /opt/hive/lib/guava-19.0.jar

ENV HIVE_HOME=/opt/hive
ENV HADOOP_HOME=/opt/hadoop
ENV PATH=/opt/hive/bin:/opt/hadoop/bin:${PATH}

# Hive 3.1.3 needs Hadoop utilities. The official Spark/Hadoop runtime is not
# coupled to this container; only the standalone metastore Thrift API is used.
RUN curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo.huaweicloud.com/apache/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz" -o /tmp/hadoop.tar.gz \
    && echo "f7eff67e948e21e23d7069dc169c98fcce757f59473e1e9a0e27d69a23df88840a9776089eeae5a8e1e496753f811868fe65638b04e3388c197931cd44d86f63  /tmp/hadoop.tar.gz" | sha512sum -c - \
    && tar -xzf /tmp/hadoop.tar.gz -C /opt \
    && mv "/opt/hadoop-${HADOOP_VERSION}" /opt/hadoop \
    && rm /tmp/hadoop.tar.gz \
    && cp /opt/hadoop/share/hadoop/common/lib/guava-27.0-jre.jar /opt/hive/lib/ \
    && curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_VERSION}/hadoop-aws-${HADOOP_VERSION}.jar" -o "/opt/hive/lib/hadoop-aws-${HADOOP_VERSION}.jar" \
    && curl --retry 5 --retry-all-errors --retry-delay 3 --connect-timeout 20 -fsSL "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_BUNDLE_VERSION}/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar" -o "/opt/hive/lib/aws-java-sdk-bundle-${AWS_SDK_BUNDLE_VERSION}.jar"

COPY hive/conf/hive-site.xml /opt/hive/conf/hive-site.xml
COPY hive/init/init-metastore.sh /opt/customer360/init-metastore.sh
RUN chmod 0555 /opt/customer360/init-metastore.sh

EXPOSE 9083
