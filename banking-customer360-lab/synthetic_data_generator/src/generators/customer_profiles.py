import numpy as np
from ..common import hashed, money, timestamps, identities, text_numbers, choose
from ..schema import table
from ..scenarios.data_quality import ranks

PROFILE_OFFSET = 1000000000


def generate(ctx, positions, owners=None):
    new = owners is not None
    owners = ctx.profile_customer_ids[positions-1] if owners is None else owners
    h = hashed(owners, ctx.seed, 30)
    rank = ranks(positions, ctx.counts['customer_profiles'], ctx.seed)
    bad = rank < ctx.dq['inconsistent_phone'] if not new else np.zeros(len(positions),dtype=bool)
    missing = rank < ctx.dq['missing_income'] if not new else np.zeros(len(positions),dtype=bool)
    suffix = np.char.zfill(owners.astype(str), 10)
    phone = np.char.add('+84-SYN-', suffix)
    for code, prefix in enumerate(['0SYN', '+84 SYN ', '0 SYN ', '0-SYN-']):
        phone = np.where(bad & (rank%4 == code), np.char.add(prefix, suffix), phone)
    income = (5000000+h%15000001)*100
    tier = hashed(owners, ctx.seed, 21)%100
    income[tier<35] = (25000000+h[tier<35]%75000001)*100
    return table('customer_profiles', dict(profile_id=positions+PROFILE_OFFSET, identity_number=identities(owners),
        phone=phone, email=np.char.add(text_numbers('synthetic.', owners), '@example.com'),
        address=np.char.add(text_numbers('Địa chỉ giả lập số ', owners), ', Khu mô phỏng ABC'),
        occupation=choose(['SYNTHETIC_ENGINEER','SYNTHETIC_TEACHER','SYNTHETIC_TRADER','SYNTHETIC_EMPLOYEE'], h),
        monthly_income=money(income, mask=missing),
        updated_at=timestamps(np.full(len(positions),ctx.ref+86400 if new else ctx.ref-1))))
