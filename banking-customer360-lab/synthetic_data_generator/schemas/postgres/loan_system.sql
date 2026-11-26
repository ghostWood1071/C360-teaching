CREATE TABLE loans (
    loan_id BIGINT NOT NULL PRIMARY KEY,
    customer_id BIGINT NOT NULL,
    loan_type TEXT NOT NULL,
    loan_amount DECIMAL(18,2) NOT NULL,
    outstanding DECIMAL(18,2) NOT NULL,
    overdue_days INT NOT NULL,
    loan_date DATE NOT NULL,
    status TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    CHECK (loan_type IN ('HOME', 'CAR', 'PERSONAL', 'BUSINESS')),
    CHECK (loan_amount > 0),
    CHECK (outstanding >= 0 AND outstanding <= loan_amount),
    CHECK (overdue_days >= 0),
    CHECK (status IN ('ACTIVE', 'CLOSED')),
    CHECK (status <> 'CLOSED' OR (outstanding = 0 AND overdue_days = 0)),
    CHECK (overdue_days = 0 OR (status = 'ACTIVE' AND outstanding > 0)),
    CHECK (updated_at::date >= loan_date)
);
