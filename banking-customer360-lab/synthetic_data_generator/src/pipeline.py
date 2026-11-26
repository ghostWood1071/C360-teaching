from pathlib import Path
import math
import shutil
import numpy as np
import pyarrow.parquet as pq
from .allocation import Allocation
from .common import batches, json_write
from .generators import GENERATORS
from .generators import incremental
from .scenarios.join_explosion import expected_metrics
from .schema import SCHEMAS, SYSTEMS
from .writers.parquet_writer import ParquetSink, read_batches, write_scan_variants
from .metrics import Measurement, disk_usage


def generate(cfg, output=None, overwrite=False):
    # Complete allocation validation before creating or deleting any output.
    ctx = Allocation(cfg)
    root = Path(output or cfg['output']['base_path']).resolve()
    if root.exists() and any(root.iterdir()) and not overwrite:
        raise ValueError(f'Output is not empty: {root}; choose another path or --overwrite')
    if overwrite and root.exists():
        if not (root/'metadata/dataset_manifest.json').exists():
            raise ValueError('--overwrite requires an existing lab dataset manifest')
        shutil.rmtree(root)
    root.mkdir(parents=True,exist_ok=True)
    with Measurement() as measurement:
        size=cfg['generation']['batch_size']
        for name,gen in GENERATORS.items():
            print(f'Generating {name}: {ctx.counts[name]:,}',flush=True)
            sink=ParquetSink(root/'batch_01'/SYSTEMS[name]/name,SCHEMAS[name],ctx.counts[name],cfg,
                file_count=cfg['output']['transaction_file_count'] if name=='transactions' else None,
                rows_per_file=cfg['output']['rows_per_file'] if name=='transactions' else None)
            for ids in batches(ctx.counts[name],size):
                sink.write(gen(ctx,ids))
            sink.close()
        if cfg['output']['generate_uniform_baseline']:
            sink=ParquetSink(root/'variants/transactions_uniform',SCHEMAS['transactions'],ctx.counts['transactions'],cfg,
                             file_count=cfg['output']['transaction_file_count'],rows_per_file=cfg['output']['rows_per_file'])
            for ids in batches(ctx.counts['transactions'],size):
                sink.write(GENERATORS['transactions'](ctx,ids,uniform=True))
            sink.close()
        months=write_scan_variants(root,cfg)
        changes=incremental.generate(ctx,root)
        raw_counts={}
        if cfg['simulation']['data_quality']['enabled']:
            for batch in ('batch_01','batch_02'):
                if batch=='batch_02' and not changes['enabled']:
                    continue
                canonical_count=ctx.counts['transactions'] if batch=='batch_01' else changes['inserts']['transactions']+changes['updates']['transactions']
                duplicates=ctx.dq['duplicate_transactions'] if batch=='batch_01' else math.floor(canonical_count*cfg['simulation']['data_quality']['duplicate_transaction_ratio'])
                repeated=ctx.dq['repeated_delivery_events']
                if canonical_count==0 and (duplicates or repeated):
                    raise ValueError('Cannot duplicate an empty transaction batch')
                sink=ParquetSink(root/'raw_delivery'/batch/'transactions',SCHEMAS['transactions'],canonical_count+duplicates+repeated,cfg)
                path=root/batch/'core_banking/transactions'
                for data in read_batches(path,batch_size=size):
                    sink.write(data)
                remaining=duplicates+repeated
                while remaining:
                    for data in read_batches(path,batch_size=size):
                        take=min(remaining,len(data))
                        sink.write(data.slice(0,take))
                        remaining-=take
                        if not remaining:
                            break
                sink.close()
                raw_counts[batch]=dict(canonical=canonical_count,duplicate_events=duplicates,repeated_events=repeated,total=canonical_count+duplicates+repeated)
        pq.write_table(expected_metrics(ctx),root/'metadata_expected.tmp.parquet',compression=cfg['generation']['compression'])
        (root/'metadata').mkdir(exist_ok=True)
        (root/'metadata_expected.tmp.parquet').rename(root/'metadata/expected_customer_metrics.parquet')
        json_write(root/'metadata/scenario_manifest.json',ctx.manifest())
        json_write(root/'metadata/data_quality_manifest.json',dict(**ctx.dq,raw_delivery=raw_counts,
            configured_profiles=cfg['volume']['customer_profiles'],actual_profiles=ctx.counts['customer_profiles']))
        json_write(root/'metadata/incremental_manifest.json',changes)
        json_write(root/'metadata/schema_manifest.json',{n:[dict(name=f.name,type=str(f.type),nullable=f.nullable) for f in s] for n,s in SCHEMAS.items()})
    manifest=dict(config=cfg,expected_counts=ctx.counts,months=months,generation=measurement.result(),status='generated',
                  note='All values are synthetic. No downstream transformations were implemented.')
    json_write(root/'metadata/dataset_manifest.json',manifest)
    manifest['storage']=disk_usage(root)
    json_write(root/'metadata/dataset_manifest.json',manifest)
    print(f'Generated {root}: {manifest["generation"]}',flush=True)
    return root
