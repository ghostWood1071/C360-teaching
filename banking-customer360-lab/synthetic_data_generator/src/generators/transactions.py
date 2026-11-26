import numpy as np
from ..common import hashed, money, timestamps, text_numbers, choose
from ..schema import table


def relationship(ctx, ids, uniform=False):
    r = ctx.tx_ranks(ids)
    hot_total = 0 if uniform else sum(ctx.hot_counts)
    cohort = (r >= hot_total) & (r < hot_total+ctx.cohort_tx_count)
    pool = ctx.uniform_accounts if uniform else ctx.background_accounts
    accounts = pool[(r-hot_total-ctx.cohort_tx_count) % len(pool)]
    begin = 0
    if not uniform:
        for account, count in zip(ctx.hot_accounts,ctx.hot_counts):
            accounts[(r>=begin) & (r<begin+count)] = account
            begin += count
    if ctx.cohort_tx_count:
        j = ctx.cfg['simulation']['join_explosion']
        accounts[cohort] = ctx.cohort_accounts[(r[cohort]-hot_total)//j['transactions_per_account']]
    return accounts, cohort, r-hot_total


def wide_text(ids, seed, length, label, stream):
    value = np.full(len(ids), label)
    for block in range((length+19)//20):
        value = np.char.add(value, np.char.add(np.char.zfill(hashed(ids, seed, stream+block).astype(str),19), '-'))
    return value.astype(f'U{length}')


def generate(ctx, ids, uniform=False, new_accounts=None, new_owners=None, late_mask=None):
    new = new_accounts is not None
    h = hashed(ids, ctx.seed, 50)
    if new:
        accounts, owners = new_accounts, new_owners
        cohort, cohort_rank = np.zeros(len(ids),dtype=bool), np.zeros(len(ids),dtype=np.int64)
    else:
        accounts, cohort, cohort_rank = relationship(ctx, ids, uniform)
        owners = ctx.account_owner[accounts]
    amount = (10000+h%9990001)*100
    success = h%100 < 94
    credit = h%2 == 0
    event_time = ctx.start + hashed(ids,ctx.seed,51) % (ctx.ref-ctx.start)
    if new:
        event_time = ctx.ref+14400+h%36000
        if late_mask is not None:
            event_time[late_mask] = ctx.ref-60*86400+h[late_mask]%(29*86400)
    else:
        inactive = ctx.inactive[owners-1]
        if inactive.any():
            event_time[inactive] = ctx.start+h[inactive]%(ctx.ref-91*86400-ctx.start)
        event_time[cohort] = ctx.ref-30*86400+h[cohort]%(30*86400)
        amount[cohort], success[cohort] = 100000000, True
        j = ctx.cfg['simulation']['join_explosion']
        credit[cohort] = cohort_rank[cohort]%j['transactions_per_account'] < j['transactions_per_account']//2
    widths = ctx.cfg['descriptive_columns']
    return table('transactions', dict(transaction_id=ids, account_id=accounts,
        transaction_type=np.where(credit,'CREDIT','DEBIT'), amount=money(amount),
        transaction_time=timestamps(event_time), channel=choose(['ATM','MOBILE','INTERNET','BRANCH'],h//7),
        merchant_category=choose(['SYN_GROCERY','SYN_TRAVEL','SYN_RETAIL','SYN_PAYROLL','SYN_UTILITIES'],h//13),
        merchant_name=wide_text(ids,ctx.seed,widths['merchant_name'],'ABC-SYN-',100),
        description=wide_text(ids,ctx.seed,widths['description'],'SYNTHETIC-PAYMENT-',200),
        reference_number=text_numbers('ABC-SYN-TX-',ids,14), status=np.where(success,'SUCCESS','FAILED'),
        updated_at=timestamps(np.full(len(ids),ctx.ref+86400 if new else ctx.ref-1))))
