from pathlib import Path
import math
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc


class ParquetSink:
    """Bounded-memory writer with exact file count and balanced file row counts."""
    def __init__(self, path, schema, count, cfg, file_count=None, rows_per_file=None):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.schema, self.cfg, self.count = schema, cfg, count
        if rows_per_file:
            file_count = max(1, math.ceil(count/rows_per_file))
            self.targets = [min(rows_per_file, count-i*rows_per_file) for i in range(file_count)]
        else:
            file_count = min(max(1, file_count or math.ceil(count/cfg['generation']['batch_size'])), max(count,1))
            self.targets = [count//file_count + (i<count%file_count) for i in range(file_count)]
        self.file_index, self.in_file, self.written, self.writer = 0, 0, 0, None

    def write(self, data):
        if data.schema != self.schema:
            raise ValueError('Writer schema mismatch')
        offset = 0
        while offset < data.num_rows:
            if self.file_index >= len(self.targets):
                raise ValueError('Writer received more than configured row count')
            if self.writer is None:
                self.writer = pq.ParquetWriter(self.path/f'part-{self.file_index:05d}.parquet', self.schema,
                    compression=self.cfg['generation']['compression'], write_statistics=True)
            take = min(data.num_rows-offset, self.targets[self.file_index]-self.in_file)
            self.writer.write_table(data.slice(offset,take), row_group_size=self.cfg['generation']['row_group_size'])
            offset += take
            self.in_file += take
            self.written += take
            if self.in_file == self.targets[self.file_index]:
                self.writer.close()
                self.writer = None
                self.in_file = 0
                self.file_index += 1

    def close(self):
        if self.writer is not None:
            self.writer.close()
            self.writer = None
        if self.written != self.count:
            raise ValueError(f'Expected {self.count} rows, wrote {self.written}')
        if self.count == 0:
            pq.write_table(pa.Table.from_batches([], schema=self.schema), self.path/'part-00000.parquet',
                           compression=self.cfg['generation']['compression'])


def read_batches(path, columns=None, batch_size=50000):
    for file in sorted(Path(path).rglob('*.parquet')):
        for batch in pq.ParquetFile(file).iter_batches(batch_size=batch_size, columns=columns):
            yield pa.Table.from_batches([batch])


def write_scan_variants(root, cfg):
    source = Path(root)/'batch_01/core_banking/transactions'
    size = cfg['generation']['batch_size']
    from ..schema import SCHEMAS
    schema = SCHEMAS['transactions']
    counts, statuses = {}, {'FAILED':0,'SUCCESS':0}
    for data in read_batches(source, ['transaction_time','status'], size):
        month = pc.strftime(data['transaction_time'], format='%Y-%m').to_numpy()
        for m,n in zip(*np.unique(month,return_counts=True)):
            counts[str(m)] = counts.get(str(m),0)+int(n)
        for status in statuses:
            statuses[status] += pc.sum(pc.cast(pc.equal(data['status'],status),pa.int64())).as_py()
    if cfg['output']['generate_month_partitioned_variant']:
        sinks = {m:ParquetSink(Path(root)/'variants/transactions_month_partitioned'/f'transaction_month={m}',
                              schema,n,cfg,rows_per_file=cfg['output']['rows_per_file'] or math.ceil(cfg['volume']['transactions']/cfg['output']['transaction_file_count']))
                 for m,n in counts.items()}
        for data in read_batches(source,batch_size=size):
            month = pc.strftime(data['transaction_time'], format='%Y-%m')
            for m,sink in sinks.items():
                sink.write(data.filter(pc.equal(month,m)))
        for sink in sinks.values():
            sink.close()
    if cfg['output']['generate_pushdown_variant']:
        total_files = max(2,cfg['output']['transaction_file_count'])
        failed_files = max(1, round(total_files*statuses['FAILED']/max(sum(statuses.values()),1)))
        for status,files in [('FAILED',failed_files),('SUCCESS',max(1,total_files-failed_files))]:
            # Separate file prefixes avoid overwriting while preserving a flat dataset.
            path = Path(root)/'variants/transactions_pushdown_friendly'/status.lower()
            sink = ParquetSink(path,schema,statuses[status],cfg,file_count=files,rows_per_file=cfg['output']['rows_per_file'])
            for data in read_batches(source,batch_size=size):
                sink.write(data.filter(pc.equal(data['status'],status)))
            sink.close()
            for file in path.glob('*.parquet'):
                file.rename(path.parent/f'{status.lower()}-{file.name}')
            path.rmdir()
    return counts
