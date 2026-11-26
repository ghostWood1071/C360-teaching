import calendar
import hashlib
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from .schema import MONEY, TIME


def hashed(ids, seed=42, stream=0):
    x = np.asarray(ids, dtype=np.uint64) + np.uint64((seed + 104729 * stream) % (2**64))
    with np.errstate(over='ignore'):
        x = (x ^ (x >> 30)) * np.uint64(0xbf58476d1ce4e5b9)
        x = (x ^ (x >> 27)) * np.uint64(0x94d049bb133111eb)
        x = x ^ (x >> 31)
    return (x & np.uint64(0x7fffffffffffffff)).astype(np.int64)


def money(cents, mask=None):
    # Arrow decimal cast is exact: integers become whole decimals, then scale by 100.
    base = pc.cast(pa.array(np.asarray(cents, dtype=np.int64), mask=mask), pa.decimal128(19, 0))
    return pc.cast(pc.divide(base, pa.scalar(100, type=pa.decimal128(3, 0))), MONEY)


def cents(column):
    # String conversion is unnecessary; the decimal arithmetic remains exact.
    return pc.cast(pc.multiply(pc.fill_null(column, pa.scalar(0, type=MONEY)),
                              pa.scalar(100, type=pa.decimal128(3, 0))), pa.int64()).to_numpy(zero_copy_only=False)


def timestamps(seconds):
    return pa.array(np.asarray(seconds, dtype=np.int64) * 1000000, type=TIME)


def seconds(column):
    return pc.cast(column, pa.int64()).to_numpy(zero_copy_only=False) // 1000000


def dates(days, mask=None):
    return pa.array(np.asarray(days, dtype=np.int32), mask=mask, type=pa.date32())


def text_numbers(prefix, ids, width=10):
    return np.char.add(prefix, np.char.zfill(np.asarray(ids).astype(str), width))


def identities(ids):
    return text_numbers('FICTIONAL-ABC-', ids)


def history_start(ref, months):
    # Exactly N consecutive calendar months, ending at the reference instant.
    month_index = ref.year * 12 + ref.month - 1
    if ref.day == 1 and ref.hour == ref.minute == ref.second == ref.microsecond == 0:
        month_index -= 1
    start_index = month_index - months + 1
    return int(ref.replace(year=start_index // 12, month=start_index % 12 + 1,
                           day=1, hour=0, minute=0, second=0, microsecond=0).timestamp())


def json_write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')


def batches(count, size, start=1):
    for lo in range(start, start + count, size):
        yield np.arange(lo, min(lo + size, start + count), dtype=np.int64)


def choose(values, codes):
    return np.asarray(values)[np.asarray(codes) % len(values)]
