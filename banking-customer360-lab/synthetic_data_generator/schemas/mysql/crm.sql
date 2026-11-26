CREATE TABLE customer_profiles (
    profile_id BIGINT NOT NULL PRIMARY KEY,
    identity_number VARCHAR(64) NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    occupation TEXT,
    monthly_income DECIMAL(18,2),
    updated_at TIMESTAMP(6) NOT NULL,
    UNIQUE (identity_number),
    CHECK (monthly_income IS NULL OR monthly_income >= 0)
);
