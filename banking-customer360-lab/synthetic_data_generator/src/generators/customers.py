import numpy as np
import pyarrow as pa
from ..common import hashed, identities, timestamps, dates, choose, text_numbers
from ..schema import table


def generate(ctx, ids, new=False):
    h = hashed(ids, ctx.seed, 10)
    corp = h % 10000 < int(ctx.cfg['distribution']['corporate_customer_ratio']*10000) if new else ctx.corporate[ids-1]
    names = np.char.add(np.char.add(choose(['Nguyễn','Trần','Lê','Phạm','Hoàng','Vũ','Đặng','Bùi'], h), ' '),
                        choose(['Minh Anh','Thu Hà','Quang Huy','Thanh Bình','Ngọc Lan','Đức Long','Hải Yến'], h//11))
    names = np.where(corp, text_numbers('Công ty Giả Lập ABC ', ids), names)
    created = np.full(len(ids), ctx.ref+3600) if new else ctx.start-5*365*86400+h%(365*86400)
    updated = np.full(len(ids), ctx.ref+86400 if new else ctx.ref-1)
    birth = ctx.ref//86400-(20*365+h%(55*365))
    return table('customers', dict(customer_id=ids, full_name=names, identity_number=identities(ids),
        date_of_birth=dates(birth, mask=corp), gender=pa.array(choose(['M','F'], h//17), mask=corp),
        customer_type=np.where(corp,'CORPORATE','INDIVIDUAL'), created_at=timestamps(created), updated_at=timestamps(updated)))
