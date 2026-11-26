# Ma trận tương thích Phase 2

| Thành phần | Phiên bản | ARM64 thực nghiệm | AMD64 |
|---|---:|---|---|
| Spark / Delta | 3.5.6 / 3.2.0 | Đạt smoke test | Image/build hỗ trợ |
| Hive Metastore | 3.1.3 | Đạt PostgreSQL + S3A | Image/build hỗ trợ |
| Trino | 484 | Đạt Delta + Ranger | Manifest upstream |
| Ranger | 2.7.0 | Image Apache, đạt policy test | Manifest upstream |
| Airflow / Docker provider | 2.10.5 / 4.0.0 | Đạt DAG smoke test | Manifest upstream |
| PostgreSQL | 16.6 | Đạt persistence test | Manifest upstream |
| MinIO | RELEASE.2025-10-15T17-29-55Z | Build source và đạt | Build source hỗ trợ |

Hive 3.1.3 dùng Hadoop AWS 3.1.4 và AWS SDK bundle 1.11.271. Trino 484 dùng native Ranger system access control và password authentication qua HTTPS.

AMD64 chưa được chạy trên host Apple Silicon hiện tại; trạng thái AMD64 xác nhận manifest/build path và Compose render hợp lệ, không ghi nhận là runtime-tested.
