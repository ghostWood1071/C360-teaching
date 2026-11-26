import math
import numpy as np


def hot_allocations(cfg):
    spec = cfg['simulation']['skew']
    if not spec['enabled']:
        return [], []
    total = cfg['volume']['transactions']
    return ([int(x['account_id']) for x in spec['hot_accounts']],
            [int(x.get('transaction_count', math.floor(total * x.get('ratio', 0))))
             for x in spec['hot_accounts']])


def permutation_parameters(count, seed):
    multiplier = 104729 + seed * 2
    while math.gcd(multiplier, count) != 1:
        multiplier += 1
    return multiplier, (seed * 8191) % count
