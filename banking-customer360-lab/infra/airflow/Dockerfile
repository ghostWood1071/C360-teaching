ARG AIRFLOW_VERSION=2.10.5
FROM apache/airflow:${AIRFLOW_VERSION}-python3.11 AS builder

ARG AIRFLOW_VERSION=2.10.5
ARG AIRFLOW_DOCKER_PROVIDER_VERSION=4.0.0

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential liblz4-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

USER airflow
COPY infra/airflow/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir \
    --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-3.11.txt" \
    -r /tmp/requirements.txt

FROM apache/airflow:${AIRFLOW_VERSION}-python3.11
COPY --chown=airflow:root --from=builder /home/airflow/.local /home/airflow/.local
COPY --chmod=0555 infra/airflow/init-airflow.sh /opt/airflow/init-airflow.sh
