CREATE TABLE customers (
    customer_id BIGINT NOT NULL PRIMARY KEY,
    full_name TEXT NOT NULL,
    identity_number TEXT NOT NULL,
    date_of_birth DATE,
    gender TEXT,
    customer_type TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    UNIQUE (identity_number),
    CHECK (customer_type IN ('INDIVIDUAL', 'CORPORATE')),
    CHECK (updated_at >= created_at)
);

CREATE TABLE accounts (
    account_id BIGINT NOT NULL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    account_type TEXT NOT NULL,
    balance DECIMAL(18,2) NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CHECK (account_type IN ('SAVING', 'CURRENT')),
    CHECK (status IN ('ACTIVE', 'CLOSED')),
    CHECK (balance >= 0),
    CHECK (status <> 'CLOSED' OR balance = 0),
    CHECK (updated_at >= created_at)
);

CREATE TABLE transactions (
    transaction_id BIGINT NOT NULL PRIMARY KEY,
    account_id BIGINT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount DECIMAL(18,2) NOT NULL,
    transaction_time TIMESTAMPTZ NOT NULL,
    channel TEXT NOT NULL,
    merchant_category TEXT NOT NULL,
    merchant_name TEXT NOT NULL,
    description TEXT NOT NULL,
    reference_number TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    CHECK (transaction_type IN ('CREDIT', 'DEBIT')),
    CHECK (amount > 0),
    CHECK (status IN ('SUCCESS', 'FAILED')),
    CHECK (channel IN ('ATM', 'MOBILE', 'INTERNET', 'BRANCH')),
    CHECK (updated_at >= transaction_time)
);
