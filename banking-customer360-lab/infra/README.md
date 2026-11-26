# Infrastructure

- `compose*.yaml`: base và overlay security/audit/distributed/sources.
- Các thư mục theo service chứa Dockerfile và cấu hình.
- `scripts/`: setup, up/down, healthcheck, smoke/security test.
- `tests/`: static infrastructure tests.
- `evidence/`: output đo runtime, bị ignore theo mẫu `docker-stats*.csv`.

Xem [tài liệu vận hành](../docs/infra/README.md).

Phase 3 dùng lại stack này qua `spark-runner` tạm thời để debug và DockerOperator cho Airflow. Job, config và SQL nằm tại `spark/jobs/phase3/` và `sql/phase3/`; không có Spark master/worker thường trực.
