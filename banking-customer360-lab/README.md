# Banking Customer 360 Lab

Project có bốn thư mục nghiệp vụ chính:

```text
├── docs/                       # Hướng dẫn generator và từng service
├── synthetic_data_generator/  # Code, config, schema, CLI và test sinh dữ liệu
├── infra/                      # Docker Compose, service config và script vận hành
└── data/                       # Dữ liệu sinh ra; bị Git ignore
```

Các file root như `Makefile`, `.env.example`, `pytest.ini` chỉ là entrypoint/cấu hình chung.

## Sinh dữ liệu

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r synthetic_data_generator/requirements.txt
make generate-small
make validate-small
```

Xem [hướng dẫn generator](docs/generator/usage.md).

## Dựng hạ tầng

```bash
make setup
make up
make smoke-test
```

Security profile:

```bash
make up-security
make security-test
```

Xem [hướng dẫn hạ tầng](docs/infra/README.md).

## Phase 3 – Source → Bronze → Silver

```bash
make up
make phase3-prepare-small
make phase3-verify
```

Sau đó chạy DAG `customer360_ingestion_pipeline` trong Airflow: Full Load `batch_01` trước, Incremental Load `batch_02` sau. Xem [hướng dẫn Phase 3](docs/phase3/README.md) và [báo cáo nghiệm thu](reports/phase3/implementation_report.md).

## Kiểm thử

```bash
python -m pytest -q
docker compose --env-file .env -f infra/compose.yaml config --quiet
```

Không commit `.env`, private key, password database hoặc nội dung trong `data/`.
