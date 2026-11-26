import numpy as np
from ..common import hashed, money, timestamps, choose
from ..schema import table


def generate(ctx, ids, owners=None):
    new = owners is not None
    owners = ctx.account_owner[ids] if owners is None else owners
    h = hashed(ids, ctx.seed, 20)
    tier = hashed(owners, ctx.seed, 21) % 100
    balance = np.where(tier < 10, (1200000000+h%800000001)*100,
                       np.where(tier < 35, (220000000+h%180000001)*100, (1000000+h%49000001)*100))
    closed = h%100 < 8
    if not new:
        cohort = ctx.cohort_account_index[ids] >= 0
        balance[cohort], closed[cohort] = 10000000000, False
        closed[np.isin(ids, ctx.hot_accounts)] = False
    balance[closed] = 0
    created = np.full(len(ids),ctx.ref+7200) if new else ctx.start-730*86400+h%(365*86400)
    return table('accounts', dict(account_id=ids, customer_id=owners, account_type=choose(['SAVING','CURRENT'],h),
        balance=money(balance), status=np.where(closed,'CLOSED','ACTIVE'), created_at=timestamps(created),
        updated_at=timestamps(np.full(len(ids),ctx.ref+86400 if new else ctx.ref-1))))
