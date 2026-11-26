# Hướng dẫn Synthetic Data Generator

## Cài đặt

```bash
python -m venv .venv
source .venv/bin/activate                # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r synthetic_data_generator/requirements.txt
```

## Sinh và kiểm định

```bash
make generate-small
make validate-small
make generate-standard
make validate-standard
```

Lệnh trực tiếp:

```bash
python synthetic_data_generator/scripts/generate_data.py \
  --config synthetic_data_generator/configs/small.yaml \
  --output data/small
python synthetic_data_generator/scripts/profile_data.py --data-path data/small
python synthetic_data_generator/scripts/validate_data.py --data-path data/small
```

`--scenario` hỗ trợ `data_skew`, `join_explosion`, `broadcast_join`, `partitioning`, `scan_optimization`, `data_quality`, `incremental`. Chỉ dùng `--overwrite` khi chủ động thay dataset đã có manifest.

Mọi output đặt dưới `data/`. Thư mục này bị Git ignore và không được push lên repository.
