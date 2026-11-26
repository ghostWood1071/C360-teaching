# Thiết kế ingestion

`prepare_phase3_sources.py` không sinh lại dữ liệu. Utility mirror Parquet và năm manifest hiện có vào `s3a://raw/<profile>/`, giữ nguyên `batch_01`, `batch_02` và `raw_delivery`. Metadata nhỏ được dùng làm nguồn sự thật cho count và scenario.

Bronze giữ nguyên cột nghiệp vụ và thêm `_source_system`, `_batch_id`, `_ingested_at`. Giao dịch dùng raw delivery nên cố ý giữ event lặp. Retry cùng batch dùng Delta `replaceWhere` trên `_batch_id`, không append lần hai và không ghi đè batch khác.

Mixed mode tạo staging table có tên `phase3_<batch_id>_<table>`. Đây là mô phỏng giao hàng incremental theo batch, không phải CDC từ transaction log. JDBC mặc định dùng hai partition; bounds chỉ chia stride đọc và không phải điều kiện lọc incremental.

Namespace `lab02_bronze` và `lab03_silver` cô lập DAG minh họa khỏi pipeline chính.
