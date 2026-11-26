# Delta Lake, MinIO và Hive Metastore

Spark dùng Delta extension và `DeltaCatalog`; file dữ liệu/log nằm ở `s3a://warehouse/...`, còn Hive Metastore chỉ giữ database, table, schema và location. PostgreSQL bền vững hóa metastore. Không lưu file Delta trong PostgreSQL.

Luồng smoke test:

1. Tạo database `smoke_test` và Delta table ngoài tại `s3a://warehouse/smoke_test/<table>`.
2. Đăng ký table với `USING DELTA LOCATION`.
3. Append một dòng.
4. `MERGE` cập nhật ID 2 và thêm ID 4.
5. Đọc version 0 để xác nhận time travel.
6. Trino đọc cùng metadata từ HMS và cùng file từ MinIO.

`submit-wrapper.sh` ánh xạ `SPARK_S3_ACCESS_KEY/SECRET_KEY` vào Hadoop configuration lúc khởi chạy. Spark identity có quyền đọc/ghi/xóa cần cho Delta transaction log. Trino identity chỉ có `ListBucket/GetObject`, và catalog tắt register-table procedure.

Layout:

```text
raw/
  core_banking/ crm/ loan_system/ incremental/
warehouse/
  bronze/ silver/ gold/ lab/ smoke_test/
spark-logs/
```

`.keep` chỉ tạo prefix giáo dục, không phải dữ liệu nghiệp vụ. Phase 2 không triển khai pipeline Customer 360 hoàn chỉnh.

Kiểm tra tay trong Spark container:

```bash
docker compose --env-file .env -f infra/compose.yaml run --rm \
  -e SPARK_S3_ACCESS_KEY -e SPARK_S3_SECRET_KEY spark-history \
  spark-submit /opt/spark/jobs/smoke_tests/storage_test.py
```

Trong thực hành, ưu tiên DAG để giữ đúng giới hạn tài nguyên và event log.
