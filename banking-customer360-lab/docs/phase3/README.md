# Phase 3 – Data Ingestion và Silver Transformation

Phase 3 triển khai pipeline chạy được từ năm nguồn nghiệp vụ đến năm bảng Bronze và bốn bảng Silver. Phạm vi dừng ở Silver; không tạo Gold, streaming, SCD2 hoặc bài tối ưu hiệu năng nâng cao.

## Bắt đầu nhanh

```bash
make up
make phase3-prepare-small
```

Mở Airflow tại `http://localhost:8083`, chạy `customer360_ingestion_pipeline` với Full Load `batch_01`, sau đó chạy Incremental Load `batch_02`. Dùng Trino tại `http://localhost:8084` để chạy SQL trong `infra/sql/phase3/`.

Các lab thực hành nằm trong `docs/labs/phase3/`. Code tham chiếu nằm trong `infra/spark/jobs/phase3/`; bài tập TODO độc lập ở `infra/spark/jobs/phase3/exercises/` và không được pipeline gọi.

## Lệnh cho từng lab

| Lab | Cách chạy |
|---|---|
| 01 Source Exploration | Trigger DAG `lab_01_source_exploration`. |
| 02 Bronze Full Load | Trigger DAG `lab_02_bronze_ingestion`. |
| 03–04 Silver/Identity | Chạy pipeline Full Load hoặc DAG `lab_03_silver_transformation` sau khi Bronze chính sẵn sàng. |
| 05 Incremental | Trigger `customer360_ingestion_pipeline` với `load_type=incremental`, `batch_id=batch_02`. |
| 06 Quality | Giữ `enable_quality_checks=true`; chạy SQL trong `infra/sql/phase3/`. |
| 07 Recovery | Trên bộ small, đặt `inject_failure=true`, quan sát fail sau Bronze commit, sau đó đặt false và retry. |

Chạy job độc lập để debug:

```bash
docker compose --env-file .env -f infra/compose.yaml --profile tools run --rm spark-runner \
  spark-submit --master 'local[2]' --driver-memory 1g \
  /opt/spark/jobs/phase3/profile_sources.py \
  --profile small --batch-id batch_01 --source-mode file --run-id manual
```

Mixed mode:

```bash
python infra/scripts/prepare_phase3_sources.py --profile small --load-jdbc --batch-id batch_01
```

Để cố ý làm lại từ đầu, dùng `make reset` và xác nhận, sau đó `make up` và prepare source lại. Reset xóa volume của đúng Compose project; không có reset tự động trong DAG.

Kết quả chạy thực tế, số lượng bản ghi và các giới hạn đã kiểm thử được ghi tại [báo cáo triển khai](../../reports/phase3/implementation_report.md).
