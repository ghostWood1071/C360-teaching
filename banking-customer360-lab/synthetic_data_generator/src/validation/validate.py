from pathlib import Path
import hashlib
import json
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from ..allocation import Allocation
from ..common import cents, seconds, json_write
from ..generators import GENERATORS, incremental
from ..generators.customer_profiles import PROFILE_OFFSET
from ..schema import SCHEMAS, SYSTEMS, PRIMARY_KEYS
from ..writers.parquet_writer import read_batches
from ..metrics import Measurement, disk_usage


class Checks:
    def __init__(self):
        self.items={}

    def add(self,name,passed,actual=None,expected=None):
        item=self.items.setdefault(name,dict(name=name,passed=True,observations=0))
        item['observations']+=1
        item['passed'] &= bool(passed)
        if actual is not None:
            item['actual']=actual
        if expected is not None:
            item['expected']=expected


def ids_of(data,name):
    ids=data[PRIMARY_KEYS[name]].to_numpy().astype(np.int64)
    return ids-PROFILE_OFFSET if name=='customer_profiles' else ids


def valid_range(values, low, high):
    return len(values)==0 or (values.min()>=low and values.max()<=high)


def logical_digest(path):
    # Canonical files are in primary-key order. Fixed read batches decouple this
    # digest from generation batch sizes and Parquet row group boundaries.
    digest=hashlib.sha256()
    pending=[]
    pending_rows=0
    def consume(data):
        data=data.combine_chunks()
        sink=pa.BufferOutputStream()
        with pa.ipc.new_stream(sink,data.schema) as writer:
            writer.write_table(data,max_chunksize=10000)
        digest.update(sink.getvalue())
    for data in read_batches(path,batch_size=10000):
        offset=0
        while offset<len(data):
            take=min(10000-pending_rows,len(data)-offset)
            pending.append(data.slice(offset,take))
            pending_rows+=take
            offset+=take
            if pending_rows==10000:
                consume(pa.concat_tables(pending))
                pending,pending_rows=[],0
    if pending:
        consume(pa.concat_tables(pending))
    return digest.hexdigest()


def validate(root):
    root=Path(root).resolve()
    manifest=json.loads((root/'metadata/dataset_manifest.json').read_text())
    cfg=manifest['config']
    ctx=Allocation(cfg)
    check=Checks()
    counts, fingerprints={},{}
    n=ctx.counts['customers']
    a=ctx.counts['accounts']
    actual_owners=np.zeros(a+1,dtype=np.int64)
    acct_count=np.zeros(n+1,dtype=np.int64)
    balance=np.zeros(n+1,dtype=np.int64)
    loan_count=np.zeros(n+1,dtype=np.int64)
    loan_amount=np.zeros(n+1,dtype=np.int64)
    outstanding=np.zeros(n+1,dtype=np.int64)
    overdue_customers=np.zeros(n+1,dtype=bool)
    tx_count=np.zeros(a+1,dtype=np.int64)
    tx_30d=np.zeros(n+1,dtype=np.int64)
    tx_credit=np.zeros(n+1,dtype=np.int64)
    tx_debit=np.zeros(n+1,dtype=np.int64)
    last_tx=np.zeros(n+1,dtype=np.int64)
    income=np.full(n+1,-1,dtype=np.int64)
    corporate=np.zeros(n+1,dtype=bool)
    seen_by_table={}
    raw_metrics={}
    months={}
    overdue_arrow_bytes=0
    overdue_records=0
    size=cfg['generation']['batch_size']
    with Measurement() as measurement:
        for name in ('customers','accounts','customer_profiles','loans','transactions'):
            path=root/'batch_01'/SYSTEMS[name]/name
            seen=np.zeros(ctx.counts[name]+1,dtype=np.uint32)
            total=0
            missing,bad_phone,overdue=0,0,0
            for data in read_batches(path,batch_size=size):
                total+=len(data)
                check.add(f'{name}.schema',data.schema==SCHEMAS[name])
                ids=ids_of(data,name)
                legal=valid_range(ids,1,ctx.counts[name])
                check.add(f'{name}.key_domain',legal)
                if not legal:
                    continue
                np.add.at(seen,ids,1)
                for f in SCHEMAS[name]:
                    if not f.nullable:
                        check.add(f'{name}.not_null.{f.name}',data[f.name].null_count==0)
                check.add(f'{name}.deterministic_row_values',data.equals(GENERATORS[name](ctx,ids)))
                updated=seconds(data['updated_at'])
                check.add(f'{name}.initial_watermark',bool(np.all(updated<ctx.ref)))
                if 'created_at' in data.column_names:
                    check.add(f'{name}.timestamps',bool(np.all(seconds(data['created_at'])<=updated)))
                if name=='customers':
                    identity=data['identity_number'].to_numpy()
                    check.add('customers.identity_unique_valid',len(np.unique(identity))==len(identity))
                    corporate[ids]=pc.equal(data['customer_type'],'CORPORATE').to_numpy()
                elif name=='accounts':
                    owners=data['customer_id'].to_numpy()
                    check.add('accounts.foreign_key',valid_range(owners,1,n))
                    if not valid_range(owners,1,n):
                        continue
                    actual_owners[ids]=owners
                    np.add.at(acct_count,owners,1)
                    values=cents(data['balance'])
                    closed=pc.equal(data['status'],'CLOSED').to_numpy()
                    check.add('accounts.closed_balance_zero',np.all(values[closed]==0))
                    check.add('accounts.balance_nonnegative',np.all(values>=0))
                    np.add.at(balance,owners,np.where(closed,0,values))
                elif name=='customer_profiles':
                    owners=ctx.profile_customer_ids[ids-1]
                    check.add('crm.identity_mapping',data['identity_number'].equals(GENERATORS['customers'](ctx,owners)['identity_number']))
                    nulls=data['monthly_income'].is_null().to_numpy()
                    missing+=int(nulls.sum())
                    values=cents(data['monthly_income'])
                    income[owners]=np.where(nulls,-1,values)
                    canonical=pc.match_substring_regex(data['phone'],r'^\+84-SYN-[0-9]{10}$').to_numpy()
                    bad_phone+=int((~canonical).sum())
                elif name=='loans':
                    owners=data['customer_id'].to_numpy()
                    check.add('loans.foreign_key',valid_range(owners,1,n))
                    if not valid_range(owners,1,n):
                        continue
                    amount,owed=cents(data['loan_amount']),cents(data['outstanding'])
                    days=data['overdue_days'].to_numpy()
                    closed=pc.equal(data['status'],'CLOSED').to_numpy()
                    check.add('loans.financial_constraints',np.all((amount>0)&(owed>=0)&(owed<=amount)&(days>=0)))
                    check.add('loans.closed_constraints',np.all((owed[closed]==0)&(days[closed]==0)))
                    check.add('loans.overdue_active_positive',np.all((~closed[days>0])&(owed[days>0]>0)))
                    loan_days=pc.cast(data['loan_date'],pa.int32()).to_numpy().astype(np.int64)*86400
                    check.add('loans.timestamps',np.all(loan_days<=updated))
                    overdue+=int((days>0).sum())
                    overdue_records+=int((days>0).sum())
                    overdue_arrow_bytes+=data.filter(pa.array(days>0)).nbytes
                    overdue_customers[owners[days>0]]=True
                    np.add.at(loan_count,owners,1)
                    np.add.at(loan_amount,owners,amount)
                    np.add.at(outstanding,owners,np.where(closed,0,owed))
                elif name=='transactions':
                    account_ids=data['account_id'].to_numpy()
                    check.add('transactions.foreign_key',valid_range(account_ids,1,a))
                    if not valid_range(account_ids,1,a):
                        continue
                    owners=actual_owners[account_ids]
                    times=seconds(data['transaction_time'])
                    values=cents(data['amount'])
                    check.add('transactions.amount_positive',np.all(values>0))
                    check.add('transactions.timestamps',np.all((times>=ctx.start)&(times<=updated)))
                    np.add.at(tx_count,account_ids,1)
                    success=pc.equal(data['status'],'SUCCESS').to_numpy()
                    np.maximum.at(last_tx,owners,np.where(success,times,0))
                    window=success&(times>=ctx.ref-30*86400)&(times<ctx.ref)
                    credit=pc.equal(data['transaction_type'],'CREDIT').to_numpy()
                    np.add.at(tx_30d,owners,window.astype(np.int64))
                    np.add.at(tx_credit,owners,np.where(window&credit,values,0))
                    np.add.at(tx_debit,owners,np.where(window&~credit,values,0))
                    for month,count in zip(*np.unique(pc.strftime(data['transaction_time'],format='%Y-%m').to_numpy(),return_counts=True)):
                        months[str(month)]=months.get(str(month),0)+int(count)
            counts[name]=total
            check.add(f'{name}.row_count',total==ctx.counts[name],total,ctx.counts[name])
            check.add(f'{name}.primary_key_unique_complete',bool(np.all(seen[1:]==1)))
            seen_by_table[name]=seen
            fingerprints[name]=logical_digest(path)
            if name=='customer_profiles':
                check.add('crm.exact_missing_income',missing==ctx.dq['missing_income'],missing,ctx.dq['missing_income'])
                check.add('crm.exact_phone_issues',bad_phone==ctx.dq['inconsistent_phone'],bad_phone,ctx.dq['inconsistent_phone'])
            if name=='loans':
                check.add('broadcast.exact_overdue_records',overdue==ctx.overdue_count,overdue,ctx.overdue_count)
                check.add('broadcast.distinct_overdue_customers',int(overdue_customers.sum())==ctx.overdue_count,int(overdue_customers.sum()),ctx.overdue_count)
        check.add('transactions.history_month_count',len(months)==cfg['simulation']['transaction_history']['months'],len(months),cfg['simulation']['transaction_history']['months'])
        never_accounts=np.flatnonzero(ctx.never[ctx.account_owner[1:]-1])+1
        check.add('business.never_transacted',np.all(tx_count[never_accounts]==0))
        for account,expected in zip(ctx.hot_accounts,ctx.hot_counts):
            check.add(f'skew.account_{account}',tx_count[account]==expected,int(tx_count[account]),expected)
            check.add(f'skew.corporate_owner_{account}',corporate[actual_owners[account]])
        cohort=ctx.cohort_customers
        expected=pq.read_table(root/'metadata/expected_customer_metrics.parquet')
        from ..scenarios.join_explosion import expected_metrics
        check.add('cohort.expected_artifact',expected.equals(expected_metrics(ctx)))
        for key,array in dict(total_accounts=acct_count,total_balance=balance,total_transactions_30d=tx_30d,
                               total_credit_30d=tx_credit,total_debit_30d=tx_debit,total_loans=loan_count,
                               total_loan_amount=loan_amount,total_outstanding=outstanding).items():
            expected_values=cents(expected[key]) if pa.types.is_decimal(expected[key].type) else expected[key].to_numpy()
            check.add(f'cohort.{key}',np.array_equal(array[cohort],expected_values))
        check.add('cohort.avg_transaction_amount_30d',np.array_equal(tx_credit[cohort]+tx_debit[cohort],
                  cents(expected['avg_transaction_amount_30d'])*tx_30d[cohort]))
        check.add('cohort.no_overdue',not overdue_customers[cohort].any())
        account_cohort=ctx.cohort_accounts
        check.add('cohort.transactions_per_account',np.all(tx_count[account_cohort]==cfg['simulation']['join_explosion']['transactions_per_account']))
        cardinality=int(np.sum(tx_30d[cohort]*loan_count[cohort]))
        check.add('cohort.detailed_join_cardinality',cardinality==ctx.manifest()['join_explosion']['expected_intermediate_rows'],cardinality,ctx.manifest()['join_explosion']['expected_intermediate_rows'])
        variants={}
        for variant in ('transactions_uniform','transactions_month_partitioned','transactions_pushdown_friendly'):
            path=root/'variants'/variant
            enabled=cfg['output'][{'transactions_uniform':'generate_uniform_baseline','transactions_month_partitioned':'generate_month_partitioned_variant','transactions_pushdown_friendly':'generate_pushdown_variant'}[variant]]
            if not enabled:
                check.add(f'{variant}.disabled_absent',not path.exists())
                continue
            seen=np.zeros(ctx.counts['transactions']+1,dtype=np.uint32)
            rows=0
            equivalent=True
            for file in sorted(path.rglob('*.parquet')):
                for batch in pq.ParquetFile(file).iter_batches(batch_size=size):
                    data=pa.Table.from_batches([batch])
                    ids=ids_of(data,'transactions')
                    check.add(f'{variant}.key_domain',valid_range(ids,1,ctx.counts['transactions']))
                    if not valid_range(ids,1,ctx.counts['transactions']):
                        equivalent=False
                        continue
                    np.add.at(seen,ids,1)
                    rows+=len(data)
                    equivalent &= data.equals(GENERATORS['transactions'](ctx,ids,uniform=variant=='transactions_uniform'))
                    if variant=='transactions_month_partitioned':
                        month=file.parent.name.split('=',1)[-1]
                        check.add(f'{variant}.partition_value',bool(pc.all(pc.equal(pc.strftime(data['transaction_time'],format='%Y-%m'),month)).as_py()))
                    if variant=='transactions_pushdown_friendly':
                        check.add(f'{variant}.status_clustered',len(pc.unique(data['status']))<=1)
            check.add(f'{variant}.logical_values',equivalent)
            check.add(f'{variant}.keys_unique_complete',np.all(seen[1:]==1))
            check.add(f'{variant}.row_count',rows==ctx.counts['transactions'],rows,ctx.counts['transactions'])
            variants[variant]=dict(rows=rows,exact_logical_equivalence=equivalent if variant!='transactions_uniform' else 'separate baseline')
        changes=incremental.change_plan(ctx)
        saved_changes=json.loads((root/'metadata/incremental_manifest.json').read_text())
        check.add('incremental.manifest',saved_changes==changes)
        if changes['enabled']:
            protected=ctx.protected_customers() if cfg['simulation']['incremental']['protect_reserved'] else np.array([],dtype=np.int64)
            for name in SCHEMAS:
                seen=np.zeros(ctx.counts[name]+changes['inserts'][name]+1,dtype=np.uint32)
                inserts,updates=0,0
                for data in read_batches(root/'batch_02'/SYSTEMS[name]/name,batch_size=size):
                    check.add(f'incremental.{name}.schema',data.schema==SCHEMAS[name])
                    ids=ids_of(data,name)
                    check.add(f'incremental.{name}.key_domain',valid_range(ids,1,len(seen)-1))
                    if not valid_range(ids,1,len(seen)-1):
                        continue
                    np.add.at(seen,ids,1)
                    new=ids>ctx.counts[name]
                    inserts+=int(new.sum())
                    updates+=int((~new).sum())
                    check.add(f'incremental.{name}.watermark',np.all(seconds(data['updated_at'])>ctx.ref))
                    for is_new in (True,False):
                        mask=new if is_new else ~new
                        if not mask.any():
                            continue
                        part=data.filter(pa.array(mask))
                        subset=ids[mask]
                        wanted=incremental.inserted(ctx,name,subset) if is_new else incremental.updated(ctx,name,subset)
                        check.add(f'incremental.{name}.full_row_images',part.equals(wanted))
                        if not is_new:
                            before=GENERATORS[name](ctx,subset)
                            check.add(f'incremental.{name}.changed',not part.equals(before))
                            owner=(part['customer_id'].to_numpy() if 'customer_id' in part.column_names else
                                   ctx.account_owner[part['account_id'].to_numpy()] if name=='transactions' else
                                   ctx.profile_customer_ids[subset-1])
                            check.add(f'incremental.{name}.reserved_protected',not np.isin(owner,protected).any())
                    if name in ('accounts','loans'):
                        check.add(f'incremental.{name}.foreign_key',valid_range(data['customer_id'].to_numpy(),1,changes['expected_counts_after_batch_02']['customers']))
                    if name=='transactions':
                        check.add('incremental.transactions.foreign_key',valid_range(data['account_id'].to_numpy(),1,changes['expected_counts_after_batch_02']['accounts']))
                        check.add('incremental.transactions.event_time',np.all(seconds(data['transaction_time'])<=seconds(data['updated_at'])))
                check.add(f'incremental.{name}.counts',inserts==changes['inserts'][name] and updates==changes['updates'][name],dict(inserts=inserts,updates=updates),dict(inserts=changes['inserts'][name],updates=changes['updates'][name]))
                check.add(f'incremental.{name}.unique_keys',np.all(seen<=1))
                check.add(f'incremental.{name}.new_keys_complete',np.all(seen[ctx.counts[name]+1:]==1))
        dq=json.loads((root/'metadata/data_quality_manifest.json').read_text())
        for key,value in ctx.dq.items():
            check.add(f'data_quality.manifest.{key}',dq.get(key)==value,dq.get(key),value)
        for batch,spec in dq['raw_delivery'].items():
            max_id=ctx.counts['transactions']+(changes['inserts']['transactions'] if batch=='batch_02' else 0)
            wanted=np.zeros(max_id+1,dtype=np.int64)
            seen=np.zeros_like(wanted)
            ordinal=0
            extra=spec['duplicate_events']+spec['repeated_events']
            for data in read_batches(root/batch/'core_banking/transactions',columns=['transaction_id'],batch_size=size):
                ids=data['transaction_id'].to_numpy()
                positions=np.arange(ordinal,ordinal+len(ids))
                wanted[ids]=1+extra//max(spec['canonical'],1)+(positions<extra%max(spec['canonical'],1))
                ordinal+=len(ids)
            equivalent=True
            for data in read_batches(root/'raw_delivery'/batch/'transactions',batch_size=size):
                ids=data['transaction_id'].to_numpy()
                if not valid_range(ids,1,max_id):
                    equivalent=False
                    continue
                np.add.at(seen,ids,1)
                if batch=='batch_01':
                    equivalent &= data.equals(GENERATORS['transactions'](ctx,ids))
                else:
                    new=ids>ctx.counts['transactions']
                    for is_new in (True,False):
                        mask=new if is_new else ~new
                        if mask.any():
                            expected_data=incremental.inserted(ctx,'transactions',ids[mask]) if is_new else incremental.updated(ctx,'transactions',ids[mask])
                            equivalent &= data.filter(pa.array(mask)).equals(expected_data)
            check.add(f'raw.{batch}.exact_delivery_multiplicity',np.array_equal(seen,wanted))
            check.add(f'raw.{batch}.unchanged_event_values',equivalent)
            check.add(f'raw.{batch}.count',int(seen.sum())==spec['total'],int(seen.sum()),spec['total'])
            raw_metrics[batch]=dict(rows=int(seen.sum()),extra_events=int(seen.sum()-ordinal))
        for name,s in SCHEMAS.items():
            check.add(f'metadata.{name}.counts',manifest['expected_counts'][name]==ctx.counts[name])
        transaction_files=[]
        hot_distribution={str(k):dict(count=int(tx_count[k]),percentage=round(float(tx_count[k]/ctx.counts['transactions']*100),6),files=0,row_groups=0) for k in ctx.hot_accounts}
        for file in sorted((root/'batch_01/core_banking/transactions').glob('*.parquet')):
            pf=pq.ParquetFile(file)
            local={str(k):0 for k in ctx.hot_accounts}
            for group in range(pf.metadata.num_row_groups):
                accounts_in_group=pf.read_row_group(group,columns=['account_id'])['account_id'].to_numpy()
                for key in ctx.hot_accounts:
                    count=int((accounts_in_group==key).sum())
                    local[str(key)]+=count
                    hot_distribution[str(key)]['row_groups']+=int(count>0)
            for key,count in local.items():
                hot_distribution[key]['files']+=int(count>0)
            transaction_files.append(dict(file=str(file.relative_to(root)),rows=pf.metadata.num_rows,
                                          bytes=file.stat().st_size,row_groups=pf.metadata.num_row_groups,hot_counts=local))
        for key,value in hot_distribution.items():
            check.add(f'skew.account_{key}.multiple_files',value['files']>1)
            check.add(f'skew.account_{key}.multiple_row_groups',value['row_groups']>1)
        if cfg['output']['rows_per_file']:
            check.add('transactions.rows_per_file',all(x['rows']<=cfg['output']['rows_per_file'] for x in transaction_files))
        else:
            check.add('transactions.file_count',len(transaction_files)==min(ctx.counts['transactions'],cfg['output']['transaction_file_count']),len(transaction_files),cfg['output']['transaction_file_count'])
        if cfg['simulation']['join_explosion']['enabled'] and len(cohort):
            check.add('business.priority_present',np.any((balance[1:]>=20000000000)&(balance[1:]<100000000000)))
        business=dict(vip=int((balance[1:]>=100000000000).sum()),priority=int(((balance[1:]>=20000000000)&(balance[1:]<100000000000)).sum()),
                      mass=int((balance[1:]<20000000000).sum()),no_transactions=int((last_tx[1:]==0).sum()),
                      inactive=int((last_tx[1:]<ctx.ref-90*86400).sum()),no_loans=int((loan_count[1:]==0).sum()),
                      overdue_customers=int(overdue_customers.sum()),missing_income=int((income[1:]<0).sum()),
                      credit_card_candidates=int(((~corporate[1:])&(income[1:]>=2000000000)&(~overdue_customers[1:])).sum()))
    items=list(check.items.values())
    report=dict(passed=all(x['passed'] for x in items),checks=items,actual_counts=counts,
                logical_fingerprints=fingerprints,variants=variants,raw_delivery=raw_metrics,business_categories=business,
                transactions_by_month=months,resources=measurement.result(),storage=disk_usage(root),
                transaction_distribution=dict(top_20_accounts=[dict(account_id=int(k),count=int(tx_count[k])) for k in np.argsort(-tx_count[1:],kind='stable')[:20]+1],
                    hot_accounts=hot_distribution,files=transaction_files),
                overdue_metrics=dict(loan_records=overdue_records,distinct_customers=int(overdue_customers.sum()),
                    loan_percentage=round(float(overdue_records/ctx.counts['loans']*100),6),
                    filtered_full_loan_arrow_bytes=overdue_arrow_bytes,
                    distinct_customer_id_arrow_bytes=int(overdue_customers.sum()*8)),
                deterministic_regeneration='Exact row values compared to stateless generator for every source and variant row; independent repeat-run test in synthetic_data_generator/tests/test_integration.py')
    json_write(root/'reports/validation_report.json',report)
    print(f'Validation: {sum(x["passed"] for x in items)}/{len(items)} checks passed; {report["resources"]}',flush=True)
    return report
