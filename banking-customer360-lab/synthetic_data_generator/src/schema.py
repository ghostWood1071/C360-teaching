import pyarrow as pa

MONEY = pa.decimal128(18, 2)
TIME = pa.timestamp('us', tz='UTC')


def schema(fields):
    return pa.schema([pa.field(name, dtype, nullable=nullable) for name, dtype, nullable in fields])


I, S, D, T, M, N = pa.int64(), pa.string(), pa.date32(), TIME, MONEY, pa.int32()
SCHEMAS = {
    'customers': schema([
        ('customer_id', I, False), ('full_name', S, False), ('identity_number', S, False),
        ('date_of_birth', D, True), ('gender', S, True), ('customer_type', S, False),
        ('created_at', T, False), ('updated_at', T, False)]),
    'accounts': schema([
        ('account_id', I, False), ('customer_id', I, False), ('account_type', S, False),
        ('balance', M, False), ('status', S, False), ('created_at', T, False), ('updated_at', T, False)]),
    'transactions': schema([
        ('transaction_id', I, False), ('account_id', I, False), ('transaction_type', S, False),
        ('amount', M, False), ('transaction_time', T, False), ('channel', S, False),
        ('merchant_category', S, False), ('merchant_name', S, False), ('description', S, False),
        ('reference_number', S, False), ('status', S, False), ('updated_at', T, False)]),
    'customer_profiles': schema([
        ('profile_id', I, False), ('identity_number', S, False), ('phone', S, True),
        ('email', S, True), ('address', S, True), ('occupation', S, True),
        ('monthly_income', M, True), ('updated_at', T, False)]),
    'loans': schema([
        ('loan_id', I, False), ('customer_id', I, False), ('loan_type', S, False),
        ('loan_amount', M, False), ('outstanding', M, False), ('overdue_days', N, False),
        ('loan_date', D, False), ('status', S, False), ('updated_at', T, False)]),
}
SYSTEMS = {'customers': 'core_banking', 'accounts': 'core_banking',
           'transactions': 'core_banking', 'customer_profiles': 'crm', 'loans': 'loan_system'}
PRIMARY_KEYS = {name: s.names[0] for name, s in SCHEMAS.items()}


def table(name, columns):
    return pa.Table.from_pydict(columns, schema=SCHEMAS[name])
