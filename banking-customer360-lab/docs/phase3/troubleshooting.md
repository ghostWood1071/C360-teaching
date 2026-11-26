# Xử lý sự cố Phase 3

| Hiện tượng | Cách kiểm tra |
|---|---|
| `Source preparation is incomplete` | Chạy `make phase3-prepare-small`; kiểm tra MinIO và prefix `raw/small/`. |
| DAG không thấy job mới | Chạy lại `spark-jobs-init` hoặc restart stack để copy job volume. |
| JDBC staging table không tồn tại | Bật source profile và chạy prepare với `--load-jdbc --batch-id ...`. |
| Bronze count lớn hơn canonical transaction | Đây là raw delivery duplicate có chủ đích; so với data_quality_manifest. |
| Conflict cùng key/timestamp | Không dùng dropDuplicates; sửa/quarantine source conflict rồi chạy lại. |
| Full Load bị từ chối | Incremental đã tồn tại; dùng reset có xác nhận nếu thật sự muốn học lại. |
| Spark OOM | Chọn profile low, dùng dataset small, giữ một slot Spark. |
| Trino chưa thấy bảng | Kiểm tra Hive Metastore, registration task và quyền Ranger. |
| Không có History event | Kiểm tra mount `spark-events`, `spark.eventLog.enabled` và quyền ghi volume. |

Lấy log bằng `docker compose --env-file .env -f infra/compose.yaml logs --tail=200 <service>`. Không chạy `docker system prune` cho bài lab.
