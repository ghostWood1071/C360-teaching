from pathlib import Path
import csv
import json
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from ..common import json_write
from ..writers.parquet_writer import read_batches
from ..metrics import Measurement, disk_usage


def profile(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'metadata/dataset_manifest.json').read_text())
    cfg=manifest['config']
    reports=root/'reports'
    reports.mkdir(exist_ok=True)
    hot=[x['account_id'] for x in json.loads((root/'metadata/scenario_manifest.json').read_text())['hot_accounts']]
    counts=np.zeros(cfg['volume']['accounts']+1,dtype=np.int64)
    per_file=[]
    month_stats={}
    statistics_rows=0
    with Measurement() as measurement:
        with (reports/'parquet_file_statistics.csv').open('w',newline='',encoding='utf-8') as stream:
            fields=['file','file_bytes','file_rows','row_group','row_group_rows','column','physical_type','compression',
                    'compressed_bytes','uncompressed_bytes','statistics_available','min','max','null_count']
            writer=csv.DictWriter(stream,fieldnames=fields)
            writer.writeheader()
            for file in sorted(root.rglob('*.parquet')):
                pf=pq.ParquetFile(file)
                md=pf.metadata
                relative=str(file.relative_to(root))
                for group in range(md.num_row_groups):
                    rg=md.row_group(group)
                    for col_index in range(rg.num_columns):
                        col=rg.column(col_index)
                        s=col.statistics
                        writer.writerow(dict(file=relative,file_bytes=file.stat().st_size,file_rows=md.num_rows,
                            row_group=group,row_group_rows=rg.num_rows,column=col.path_in_schema,
                            physical_type=col.physical_type,compression=col.compression,compressed_bytes=col.total_compressed_size,
                            uncompressed_bytes=col.total_uncompressed_size,statistics_available=s is not None,
                            min=str(s.min) if s and s.has_min_max else '',max=str(s.max) if s and s.has_min_max else '',
                            null_count=s.null_count if s else ''))
                        statistics_rows+=1
                if relative.startswith('batch_01/core_banking/transactions/'):
                    local=np.zeros(len(hot),dtype=np.int64)
                    groups={str(k):0 for k in hot}
                    for group in range(md.num_row_groups):
                        data=pf.read_row_group(group,columns=['account_id','transaction_time'])
                        ids=data['account_id'].to_numpy()
                        np.add.at(counts,ids,1)
                        for i,key in enumerate(hot):
                            c=int((ids==key).sum())
                            local[i]+=c
                            groups[str(key)]+=int(c>0)
                        months=pc.strftime(data['transaction_time'],format='%Y-%m').to_numpy()
                        for month,n in zip(*np.unique(months,return_counts=True)):
                            ms=month_stats.setdefault(str(month),dict(rows=0,canonical_files=set(),partitioned_bytes=0))
                            ms['rows']+=int(n)
                            ms['canonical_files'].add(relative)
                    per_file.append(dict(file=relative,rows=md.num_rows,bytes=file.stat().st_size,
                        hot_counts={str(k):int(c) for k,c in zip(hot,local)},hot_row_groups=groups,row_groups=md.num_row_groups))
                if relative.startswith('variants/transactions_month_partitioned/'):
                    month=file.parent.name.split('=',1)[-1]
                    month_stats.setdefault(month,dict(rows=0,canonical_files=set(),partitioned_bytes=0))['partitioned_bytes']+=file.stat().st_size
        top=np.argsort(-counts[1:],kind='stable')[:20]+1
        hot_stats={str(k):dict(count=int(counts[k]),percentage=round(float(counts[k]/max(counts.sum(),1)*100),6),
            files=sum(x['hot_counts'][str(k)]>0 for x in per_file),
            row_groups=sum(x['hot_row_groups'][str(k)] for x in per_file)) for k in hot}
        overdue_rows=overdue_bytes=0
        overdue_customers=set()
        for data in read_batches(root/'batch_01/loan_system/loans',columns=['customer_id','loan_id','overdue_days','status','outstanding'],batch_size=cfg['generation']['batch_size']):
            filtered=data.filter(pc.greater(data['overdue_days'],0))
            overdue_rows+=len(filtered)
            overdue_bytes+=filtered.nbytes
            overdue_customers.update(filtered['customer_id'].to_pylist())
        uniform_stats=None
        if cfg['output']['generate_uniform_baseline']:
            uniform_counts=np.zeros_like(counts)
            for data in read_batches(root/'variants/transactions_uniform',columns=['account_id']):
                np.add.at(uniform_counts,data['account_id'].to_numpy(),1)
            positive=uniform_counts[uniform_counts>0]
            # The deliberately reserved cohort has its own fixed allocation.
            scenario=json.loads((root/'metadata/scenario_manifest.json').read_text())
            eligible=uniform_counts.copy()
            eligible[scenario['join_explosion']['account_ids']]=0
            background=eligible[eligible>0]
            uniform_stats=dict(nonzero_accounts=int(len(positive)),min_background_count=int(background.min()) if len(background) else 0,
                               max_background_count=int(background.max()) if len(background) else 0,
                               top_20=[dict(account_id=int(k),count=int(uniform_counts[k])) for k in np.argsort(-uniform_counts[1:],kind='stable')[:20]+1])
        for month,value in month_stats.items():
            value['canonical_files']=len(value['canonical_files'])
            value['size_note']='Bytes by month are exact for Hive partitions; shared canonical files cannot be assigned wholly to one month.'
    report=dict(top_20_accounts=[dict(account_id=int(k),count=int(counts[k])) for k in top],hot_accounts=hot_stats,
                transaction_files=per_file,months=month_stats,uniform_baseline=uniform_stats,
                overdue=dict(rows=overdue_rows,distinct_customers=len(overdue_customers),
                    percentage=round(overdue_rows/cfg['volume']['loans']*100,6),filtered_arrow_bytes=overdue_bytes,
                    distinct_customer_id_arrow_bytes=pa.array(sorted(overdue_customers),type=pa.int64()).nbytes,
                    filtered_columns=['customer_id','loan_id','overdue_days','status','outstanding']),
                resources=measurement.result(),parquet_statistics_rows=statistics_rows,storage=disk_usage(root))
    json_write(reports/'profiling_report.json',report)
    lines=['# Hồ sơ dữ liệu ABC Bank','',f"Tổng dung lượng lúc đo: {report['storage']['total_bytes']:,} byte; số file Parquet: {report['storage']['parquet_file_count']}.",
           '',f"Thời gian sinh: {manifest['generation']['duration_seconds']} giây. RSS đỉnh lấy mẫu: {manifest['generation']['peak_rss_bytes_sampled']:,} byte.",
           '', '## 20 tài khoản có nhiều giao dịch nhất','','| account_id | Số giao dịch |','|---:|---:|']
    lines += [f"| {x['account_id']} | {x['count']} |" for x in report['top_20_accounts']]
    lines += ['', '## Khóa nóng','','| account_id | Số dòng | Tỷ lệ % | Số file | Số row group |','|---:|---:|---:|---:|---:|']
    lines += [f"| {k} | {x['count']} | {x['percentage']} | {x['files']} | {x['row_groups']} |" for k,x in hot_stats.items()]
    lines += ['', '## Phân bố file giao dịch','','| File | Số dòng | Byte | Khóa nóng |','|---|---:|---:|---|']
    lines += [f"| {x['file']} | {x['rows']} | {x['bytes']} | {x['hot_counts']} |" for x in per_file]
    lines += ['', '## Lịch sử tháng','','| Tháng | Số dòng | Byte bản partition | File canonical có tháng |','|---|---:|---:|---:|']
    lines += [f"| {k} | {x['rows']} | {x['partitioned_bytes']} | {x['canonical_files']} |" for k,x in sorted(month_stats.items())]
    lines += ['', 'Byte theo tháng chỉ phân bổ chính xác cho thư mục Hive. File canonical chứa nhiều tháng nên không gán toàn bộ byte cho từng tháng.',
        '',f"Quá hạn: {overdue_rows} khoản, {len(overdue_customers)} khách riêng biệt, {report['overdue']['percentage']}%; kích thước Arrow sau lọc {overdue_bytes:,} byte với 5 cột nêu trong JSON.",
        '',f"Có {statistics_rows} dòng thống kê cột/row group trong parquet_file_statistics.csv. Thống kê min/max có thể dài theo chiều rộng mô tả.",
        '', 'Phân bố nghiệp vụ và kết quả kiểm định từng quy tắc nằm trong validation_report.json. Không suy ra thời gian Spark, spill hay tốc độ tối ưu từ các số liệu này.']
    if uniform_stats:
        lines += ['',f"Baseline: giao dịch nền mỗi tài khoản đủ điều kiện từ {uniform_stats['min_background_count']} đến {uniform_stats['max_background_count']}; cohort vẫn giữ phân bổ cố định."]
    (reports/'profiling_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Profiled {root}: {report["storage"]}',flush=True)
    return report
