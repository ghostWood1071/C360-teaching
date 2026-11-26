from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
from . import customers, accounts, transactions, customer_profiles, loans
from ..common import batches, timestamps
from ..schema import SCHEMAS, SYSTEMS
from ..writers.parquet_writer import ParquetSink


def replace(data, name, column):
    return data.set_column(data.schema.get_field_index(name), data.schema.field(name),column)


def change_plan(ctx):
    s = ctx.cfg['simulation']['incremental']
    inserts = {t:s[k] if s['enabled'] else 0 for t,k in dict(customers='new_customers',
        customer_profiles='new_customer_profiles', accounts='new_accounts', transactions='new_transactions', loans='new_loans').items()}
    updates = {t:s[k] if s['enabled'] else 0 for t,k in dict(accounts='updated_accounts',
        transactions='updated_transactions',customer_profiles='updated_customer_profiles',loans='updated_loans').items()}
    updates['customers'] = 0
    return dict(enabled=s['enabled'],inserts=inserts,updates=updates,
                expected_counts_after_batch_02={t:ctx.counts[t]+inserts[t] for t in inserts},
                updated_at='reference_time + 1 day',late_arriving_transactions=s['late_arriving_transactions'] if s['enabled'] else 0)


def new_owners(ctx, count, offset=0):
    s = ctx.cfg['simulation']['incremental']
    if s['new_customers']:
        return ctx.counts['customers']+1+(np.arange(offset,offset+count)%s['new_customers'])
    pool = ctx.customer_ids[ctx.reserved_customers:]
    return pool[np.arange(offset,offset+count)%len(pool)]


def inserted(ctx, name, ids):
    if name=='customers':
        return customers.generate(ctx,ids,new=True)
    pos = ids-ctx.counts[name]-1
    if name=='customer_profiles':
        return customer_profiles.generate(ctx,ids,owners=ctx.counts['customers']+1+pos)
    if name=='accounts':
        return accounts.generate(ctx,ids,owners=new_owners(ctx,len(ids),int(pos[0])))
    if name=='loans':
        return loans.generate(ctx,ids,owners=new_owners(ctx,len(ids),int(pos[0])))
    s = ctx.cfg['simulation']['incremental']
    if s['new_accounts']:
        accounts_for_tx = ctx.counts['accounts']+1+pos%s['new_accounts']
        owners = new_owners(ctx,s['new_accounts'])[pos%s['new_accounts']]
    else:
        accounts_for_tx = ctx.background_accounts[pos%len(ctx.background_accounts)]
        owners = ctx.account_owner[accounts_for_tx]
    late = pos<s['late_arriving_transactions']
    if late.any():
        accounts_for_tx[late] = ctx.background_accounts[pos[late]%len(ctx.background_accounts)]
        owners[late] = ctx.account_owner[accounts_for_tx[late]]
    return transactions.generate(ctx,ids,new_accounts=accounts_for_tx,new_owners=owners,
                                 late_mask=late)


def updated(ctx, name, ids):
    from . import GENERATORS
    data = GENERATORS[name](ctx,ids)
    if name=='accounts':
        balance = pc.if_else(pc.equal(data['status'],'ACTIVE'),
                            pc.add(data['balance'],pa.scalar('12345.00',type=pa.string()).cast(data['balance'].type)),
                            pa.scalar(0,type=data['balance'].type))
        # Open closed accounts as part of the balance update so every image changes.
        balance = pc.if_else(pc.equal(data['status'],'CLOSED'), pa.scalar(12345,type=data['balance'].type),balance)
        data = replace(data,'balance',balance.cast(SCHEMAS[name].field('balance').type))
        data = replace(data,'status',pa.array(['ACTIVE']*len(ids)))
    elif name=='transactions':
        data = replace(data,'status',pc.if_else(pc.equal(data['status'],'SUCCESS'),'FAILED','SUCCESS'))
    elif name=='customer_profiles':
        data = replace(data,'address',pc.binary_join_element_wise(data['address'],pa.scalar(' (updated)'),''))
    elif name=='loans':
        outstanding = pc.if_else(pc.equal(data['status'],'ACTIVE'),
                                pc.divide(data['outstanding'],pa.scalar(2)),data['outstanding'])
        data = replace(data,'outstanding',pc.cast(outstanding,SCHEMAS[name].field('outstanding').type,safe=False))
    return replace(data,'updated_at',timestamps(np.full(len(ids),ctx.ref+86400)))


def generate(ctx, root):
    plan = change_plan(ctx)
    if not plan['enabled']:
        return plan
    size=ctx.cfg['generation']['batch_size']
    pools = dict(accounts=ctx.update_account_pool,loans=ctx.update_loan_pool,
                 customer_profiles=ctx.update_profile_pool,transactions=ctx.update_tx_pool)
    for name in SCHEMAS:
        sink = ParquetSink(Path(root)/'batch_02'/SYSTEMS[name]/name,SCHEMAS[name],
                           plan['inserts'][name]+plan['updates'][name],ctx.cfg)
        for ids in batches(plan['inserts'][name],size,start=ctx.counts[name]+1):
            sink.write(inserted(ctx,name,ids))
        if name in pools:
            selected = pools[name][:plan['updates'][name]]
            for offset in range(0,len(selected),size):
                sink.write(updated(ctx,name,selected[offset:offset+size]))
        sink.close()
    return plan
