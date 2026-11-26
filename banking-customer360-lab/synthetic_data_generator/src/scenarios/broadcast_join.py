import math


def overdue_count(cfg):
    s = cfg['simulation']['broadcast_join']
    return (int(s['overdue_loan_count']) if 'overdue_loan_count' in s else
            math.floor(cfg['volume']['loans'] * s['overdue_loan_ratio'])) if s['enabled'] else 0
