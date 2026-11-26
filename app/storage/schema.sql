-- Coinfidential schema (see docs/database-design.md).
-- All money columns are INTEGER minor units (paise or cents). There are no REAL columns.
-- Every statement uses IF NOT EXISTS / OR IGNORE so the script can run again safely.

CREATE TABLE IF NOT EXISTS accounts (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL CHECK (name <> ''),
    is_system  INTEGER NOT NULL DEFAULT 0 CHECK (is_system IN (0, 1)),
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- One wallet per currency per account. Only INR and USD are allowed (ADR-0001).
CREATE TABLE IF NOT EXISTS wallets (
    id         INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts (id),
    currency   TEXT    NOT NULL CHECK (currency IN ('INR', 'USD')),
    -- Cached balance. typeof() stops SQLite from quietly storing a float here.
    balance    INTEGER NOT NULL DEFAULT 0 CHECK (typeof(balance) = 'integer'),
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (account_id, currency)
);

-- One row per money movement. UNIQUE(reverses) means a transfer is reversed at most once (ADR-0002).
CREATE TABLE IF NOT EXISTS transactions (
    id         INTEGER PRIMARY KEY,
    kind       TEXT    NOT NULL CHECK (kind IN ('funding', 'transfer', 'reversal')),
    reverses   INTEGER UNIQUE REFERENCES transactions (id),
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- reverses is set for reversals and only for reversals.
    CHECK ((kind = 'reversal') = (reverses IS NOT NULL))
);

-- The debit and credit lines of each transaction. Append-only (triggers below).
-- hash = SHA-256(prev_hash + this entry's fields), see ADR-0003.
CREATE TABLE IF NOT EXISTS ledger_entries (
    id             INTEGER PRIMARY KEY,
    transaction_id INTEGER NOT NULL REFERENCES transactions (id),
    wallet_id      INTEGER NOT NULL REFERENCES wallets (id),
    direction      TEXT    NOT NULL CHECK (direction IN ('debit', 'credit')),
    amount         INTEGER NOT NULL CHECK (typeof(amount) = 'integer' AND amount > 0),
    prev_hash      TEXT    NOT NULL,
    hash           TEXT    NOT NULL UNIQUE,
    created_at     TEXT    NOT NULL
);

-- The saved result for each idempotency key a client sent (FR-2).
CREATE TABLE IF NOT EXISTS idempotency_keys (
    account_id     INTEGER NOT NULL REFERENCES accounts (id),
    idem_key       TEXT    NOT NULL CHECK (idem_key <> ''),
    request_hash   TEXT    NOT NULL,
    transaction_id INTEGER REFERENCES transactions (id),  -- NULL if the request was rejected
    status_code    INTEGER NOT NULL,
    response_body  TEXT    NOT NULL,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (account_id, idem_key)
);

-- Access tokens (ADR-0005). Only the SHA-256 hash of a token is stored, never the token.
CREATE TABLE IF NOT EXISTS tokens (
    token_hash TEXT    PRIMARY KEY,
    account_id INTEGER REFERENCES accounts (id),  -- NULL for admin tokens
    role       TEXT    NOT NULL CHECK (role IN ('user', 'admin')),
    expires_at TEXT    NOT NULL,
    created_at TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ledger_entries_wallet ON ledger_entries (wallet_id);
CREATE INDEX IF NOT EXISTS ledger_entries_transaction ON ledger_entries (transaction_id);

-- Append-only triggers (FR-4.1). RAISE(ABORT) only cancels the statement,
-- so write_transaction() still rolls back the whole transaction.
-- INSERT OR REPLACE is also blocked because each connection sets recursive_triggers=ON.
CREATE TRIGGER IF NOT EXISTS ledger_no_update BEFORE UPDATE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;

CREATE TRIGGER IF NOT EXISTS ledger_no_delete BEFORE DELETE ON ledger_entries
BEGIN SELECT RAISE(ABORT, 'ledger is append-only'); END;

CREATE TRIGGER IF NOT EXISTS transactions_no_update BEFORE UPDATE ON transactions
BEGIN SELECT RAISE(ABORT, 'transactions are append-only'); END;

CREATE TRIGGER IF NOT EXISTS transactions_no_delete BEFORE DELETE ON transactions
BEGIN SELECT RAISE(ABORT, 'transactions are append-only'); END;

-- One system account and wallet per currency. They fund new wallets and may go negative (BR-2).
INSERT OR IGNORE INTO accounts (id, name, is_system) VALUES (1, 'System INR', 1), (2, 'System USD', 1);
INSERT OR IGNORE INTO wallets (id, account_id, currency) VALUES (1, 1, 'INR'), (2, 2, 'USD');
