# Báo cáo triển khai Phase 3

Ngày nghiệm thu: **27/11/2026** (Asia/Ho_Chi_Minh). Chỉ ghi kết quả đã thực thi; không suy diễn kết quả cho dataset standard.

## Phạm vi và thành phần tái sử dụng

Đã hoàn thành Source → Bronze → Silver. Không triển khai Gold, SCD2, streaming, CDC transaction-log hoặc tối ưu Spark nâng cao.

Tái sử dụng Spark 3.5.6/Delta 3.2.0/Java 17 image, Hive Metastore, MinIO `raw`/`warehouse`, Trino 484, Spark event-log volume, Airflow LocalExecutor, pool `spark_tasks` và factory DockerOperator của Phase 2. Phase 1 schema/manifest và dữ liệu small được dùng trực tiếp, không sinh lại.

Thay đổi hạ tầng bắt buộc đã xác minh:

- Spark image thêm PyYAML để đọc config Phase 3.
- `spark-runner` là service profile `tools`, chỉ tồn tại trong thời gian debug.
- Trino MinIO identity thêm **chỉ** `GetObject` cho `warehouse/quality/*` và namespace lab; không có Put/Delete.
- DockerOperator hỗ trợ profile standard/low và whitelist JDBC environment.

## Thành phần được tạo

- 4 DAG: `lab_01_source_exploration`, `lab_02_bronze_ingestion`, `lab_03_silver_transformation`, `customer360_ingestion_pipeline`.
- 9 Spark entrypoint: profile, prepare JDBC, Bronze ingest/validate, customer master, facts, Silver validate, reconcile và READY marker.
- Module dùng chung cho config, schema, readers, writers, transformation, quality và manifest.
- 6 SQL script Trino/Spark, 7 tài liệu lab tiếng Việt và 3 exercise TODO độc lập.
- Utility `prepare_phase3_sources.py`, `verify_phase3.py` và test Phase 3.

## Tham số pipeline

`load_type`, `batch_id`, `source_mode`, `profile`, `resource_profile`, `enable_quality_checks`, `inject_failure`, `allow_reset`. Full Load yêu cầu `batch_01`; Incremental yêu cầu `batch_02`; `max_active_runs=1`. Profile DAG phải khớp profile đang deploy trong `.env`.

## Ánh xạ bảng

| Nguồn | Bronze | Silver |
|---|---|---|
| core_banking.customers | bronze.customers | silver.customer_master |
| core_banking.accounts | bronze.accounts | silver.accounts |
| raw_delivery.transactions | bronze.transactions | silver.transactions |
| crm.customer_profiles | bronze.customer_profiles | silver.customer_master |
| loan_system.loans | bronze.loans | silver.loans |

## Kết quả thực thi small

| Mốc | customers | accounts | transactions | customer_profiles | loans |
|---|---:|---:|---:|---:|---:|
| Bronze Batch 01 delivery | 10.000 | 20.000 | 40.400 | 10.000 | 10.000 |
| Silver sau Full Load | 10.000 | 20.000 | 40.000 | – | 10.000 |
| Bronze Batch 02 delivery | 20 | 240 | 1.030 | 120 | 120 |
| Silver sau Incremental | 10.020 | 20.040 | 41.000 | – | 10.020 |

Bronze Batch 01 giữ đúng 400 duplicated transaction delivery events; Batch 02 giữ đúng 10. Silver business key là duy nhất. Trino trả đúng count Silver sau incremental và đọc được Delta history (`WRITE`, hai `MERGE`).

## Quality, replay và interoperability

- Full: 21 Bronze checks, 22 Silver checks và 13 reconciliation checks đạt.
- Incremental: 21 Bronze checks, 22 Silver checks và 8 reconciliation checks đạt.
- `quality.validation_results` có 107 kết quả PASSED, 0 FAILED trong các lần validation thành công; một validation thử đầu thất bại do alias FK mơ hồ đã được sửa và không ghi false success.
- Replay Batch 02 giữ Bronze delivery count 20/240/1.030/120/120 và Silver count 20.040/41.000/10.020 không đổi.
- File mode và mixed PostgreSQL/Parquet mode đều profile thành công. JDBC staging đã nạp 10.000 customers, 20.000 accounts, 40.000 canonical transactions và 10.000 CRM profiles.
- Airflow import errors: `[]`; DAG Lab 01 chạy thật thành công và DockerOperator tạo/xóa Spark container tạm thời.
- Spark History Server hiển thị application đã hoàn tất, gồm Full, Incremental, replay và Airflow DAG test.
- Trino đọc Bronze, Silver, Quality và `$history` sau khi bổ sung quyền read-only cho quality prefix.

## Tài nguyên và thời gian quan sát

Chạy small với `local[2]`, driver 1 GiB, shuffle 4. Các application chính quan sát khoảng 5–20 giây; incremental facts MERGE khoảng 20 giây, replay MERGE khoảng 14 giây. Snapshot khi ETL stack chạy: Airflow scheduler ~543 MiB, webserver ~792 MiB, HMS ~209 MiB, PostgreSQL ~80 MiB, History Server ~228 MiB, MinIO ~448 MiB. Đây là snapshot, không phải benchmark hay peak RSS.

## Giới hạn và phần chưa kiểm thử

- Chưa chạy pipeline standard 2,3 GiB để tránh khẳng định laptop hiện tại đủ RAM; code và source preparation hỗ trợ standard.
- Mixed source dùng PostgreSQL cho CRM vì đây là source DB đã được Phase 2 xác minh; MySQL driver có trong image nhưng chưa có MySQL service trong stack.
- Chưa chạy security/Ranger profile cùng Phase 3 trong lượt nghiệm thu này; không thay đổi Ranger policy hoặc tắt authorization.
- Failure injection đã được code/test tĩnh; không cố ý tạo một Airflow run thất bại trong nghiệm thu cuối vì Bronze retry/replay đã được kiểm chứng trực tiếp.
- Các bảng Delta độc lập không có transaction nguyên tử xuyên bảng; READY marker chỉ được ghi sau dependency và reconciliation.

## Lệnh nghiệm thu

```bash
make up
make phase3-prepare-small
make phase3-verify
docker compose --env-file .env -f infra/compose.yaml exec -T airflow-scheduler \
  airflow dags test lab_01_source_exploration 2026-11-27
```

Các lệnh chạy từng lab và Spark entrypoint độc lập nằm trong `docs/phase3/README.md` và từng `docs/labs/phase3/*/README.md`.
