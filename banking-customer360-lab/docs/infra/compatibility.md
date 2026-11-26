# Ma trận phiên bản và tương thích

| Thành phần | Phiên bản | Lý do/chứng cứ |
|---|---:|---|
| Spark | 3.5.6 | Nhánh Spark 3.5, Java 17, hỗ trợ kết nối external Hive Metastore 3.1.3 |
| Delta Lake | 3.2.0 | Delta 3.2.x tương thích Spark 3.5.x |
| Hive Metastore | 3.1.3 | Catalog Thrift dùng chung, lưu metadata trong PostgreSQL |
| Trino | 484 | Delta connector, native S3 và Ranger access control |
| Airflow | 2.10.5 | LocalExecutor ổn định, Python 3.11 |
| Docker provider | 4.0.0 | Bản được constraints Airflow 2.10.5/Python 3.11 khóa; có `DockerOperator` |
| Ranger | 2.7.0 | Image Apache đa kiến trúc; mask và row filter đã kiểm thử |
| PostgreSQL | 16.6 | Backend metadata dùng chung, tách role/database |
| MinIO | RELEASE.2025-10-15T17-29-55Z | Bản security/CVE cuối; build từ source chính thức |
| MinIO Client | RELEASE.2025-08-13T08-35-41Z | Bản `mc` cuối; build chung image local |
| Solr | 9.8.1 | Chỉ dùng cho audit profile |

Nguồn chính thức: [Spark 3.5.6 và Hive](https://spark.apache.org/docs/3.5.6/sql-data-sources-hive-tables.html), [Delta compatibility](https://docs.delta.io/releases/), [Trino Delta connector](https://trino.io/docs/484/connector/delta-lake.html), [Trino Ranger](https://trino.io/docs/484/security/ranger-access-control.html), [Airflow Docker provider 4.0.0](https://airflow.apache.org/docs/apache-airflow-providers-docker/4.0.0/operators/docker.html), [Apache Ranger image](https://hub.docker.com/r/apache/ranger/tags).

Spark runtime đặt JAR Delta/S3 chính ở `/opt/spark/jars`, còn bộ Hive client 3.1.3 và dependency transitively được cô lập tại `/opt/spark/hive-metastore-jars`. Cấu hình `spark.sql.hive.metastore.jars=path` tránh trộn dependency Hive với classpath chính.

Runtime mặc định dùng image chính thức `apache/ranger:2.7.0`. Dockerfile source-build 2.6.0 được giữ làm fallback có checksum, nhưng reactor 2.6.0 hiện bị repository phụ thuộc Kylin upstream trả 401 nên không phải đường chạy mặc định.

MinIO Community hiện được upstream phân phối theo source, nên `infra/minio/Dockerfile` build hai binary chính thức bằng Go. Image Java/Spark/PostgreSQL/Trino/Ranger có manifest `linux/amd64` và `linux/arm64`; MinIO được build native từ source. Nếu cần ép Ranger chạy AMD64 để đối chiếu, dùng:

```bash
docker compose --env-file .env -f infra/compose.yaml \
  -f infra/compose.security.yaml -f infra/compose.security-amd64.yaml up -d
```

Đây là fallback chạy qua giả lập amd64, chậm hơn native. `setup` và `docker compose build` là nơi xác nhận thực tế manifest/kiến trúc trên máy học viên.
