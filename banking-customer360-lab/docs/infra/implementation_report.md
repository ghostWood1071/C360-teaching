# Báo cáo triển khai Phase 2

Ngày kiểm chứng: 27-11-2026, Docker Desktop `linux/arm64`, giới hạn khoảng 7 GiB.

## Phạm vi

Repository tham chiếu `ghostWood1071/data-platform-lab` được cố định tại commit `0156444b4f18051bc0da5829e9ef727ff26f21bd`. Topology MinIO–PostgreSQL–Hive được tái sử dụng ở mức ý tưởng; credential hard-code, Iceberg, HiveServer2, Celery/Redis và Spark cluster thường trực bị loại. Ranger 2.6.0 được đối chiếu tại tag commit `a1786ac2fe02196af9cda2ed25716310cac44d43`; runtime cuối dùng image Apache chính thức Ranger 2.7.0 đa kiến trúc.

## Kết quả thực tế

- Base stack healthy: PostgreSQL, MinIO, Hive Metastore, Airflow, Spark History Server và Trino.
- Airflow run `manual_infra_20261126T153248Z` thành công: Delta create/append/MERGE/time travel, Trino read và Spark event log.
- Trino đọc 4 dòng trước và sau restart PostgreSQL + MinIO; metadata Airflow vẫn còn.
- Ranger bootstrap tạo 5 persona và 7 policy lab. Trino log xác nhận `Loaded system access control ranger`.
- 13 security checks đạt: quyền persona, deny layer/cột, masking, row filter, mật khẩu sai, write denial, MinIO credential lạ, policy polling và audit identity.
- Snapshot base `infra/evidence/docker-stats-20261126T153428Z.csv` xấp xỉ 2,7 GiB. Airflow webserver từng dùng 757 MiB/768 MiB nên limit mặc định đã tăng lên 1 GiB.
- Snapshot security `infra/evidence/docker-stats-20261126T172838Z.csv` xấp xỉ 3,85 GiB: Trino 1,12 GiB, Ranger 698 MiB và Airflow webserver 798 MiB/1 GiB.

## Quyết định và ranh giới

- Spark 3.5.6 + Delta 3.2.0; Hive 3.1.3 dùng metastore PostgreSQL và S3A jars riêng.
- Security profile chỉ publish Trino HTTPS 8443. HTTP 8080 chỉ dành cho discovery nội bộ Docker.
- Password file dùng PBKDF2-HMAC-SHA1 đúng implementation Trino 484.
- Ranger Admin dùng `apache/ranger:2.7.0`; wrapper chỉ render cấu hình rồi gọi entrypoint Apache.
- Ranger bảo vệ đường truy cập Trino, không tự bảo vệ Spark truy cập MinIO. Storage identities được tách và giới hạn riêng.
- Solr audit là profile tùy chọn; đây không phải kiến trúc production.

## Lệnh tái hiện

```bash
make setup
make up
make smoke-test
make down
make up-security
make security-test
make stats
make down
```

## Giới hạn

- Runtime AMD64 chưa chạy trên host ARM64; manifest và Compose overlay đã render thành công.
- TLS dùng chứng thư self-signed cho lab.
- Chưa có HA, secret manager, KMS/HSM, network policy hay DR.
