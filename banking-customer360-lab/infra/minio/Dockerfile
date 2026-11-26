FROM golang:1.24.8-bookworm AS build

ARG MINIO_VERSION=RELEASE.2025-10-15T17-29-55Z
ARG MINIO_MC_VERSION=RELEASE.2025-08-13T08-35-41Z

RUN CGO_ENABLED=0 go install "github.com/minio/minio@${MINIO_VERSION}" \
    && CGO_ENABLED=0 go install "github.com/minio/mc@${MINIO_MC_VERSION}" \
    && /go/bin/minio --version \
    && /go/bin/mc --version

FROM debian:bookworm-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 minio \
    && useradd --uid 1000 --gid 1000 --home-dir /home/minio --create-home --shell /usr/sbin/nologin minio \
    && mkdir -p /data \
    && chown minio:minio /data

COPY --from=build /go/bin/minio /usr/local/bin/minio
COPY --from=build /go/bin/mc /usr/local/bin/mc

USER minio
WORKDIR /home/minio
EXPOSE 9000 9001
CMD ["minio", "server", "/data", "--console-address", ":9001"]
