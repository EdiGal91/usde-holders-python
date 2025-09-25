CREATE TABLE IF NOT EXISTS sync_state (
  id SMALLINT PRIMARY KEY DEFAULT 1,
  last_block BIGINT NOT NULL
);

INSERT INTO sync_state(id,last_block)
VALUES (1,0)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS deltas (
  block_number BIGINT NOT NULL,
  tx_hash TEXT NOT NULL,
  log_index INT NOT NULL,
  address BYTEA NOT NULL,
  amount NUMERIC(78,0) NOT NULL,
  PRIMARY KEY (block_number, tx_hash, log_index, address)
);

CREATE TABLE IF NOT EXISTS balances (
  address BYTEA PRIMARY KEY,
  balance NUMERIC(78,0) NOT NULL
);

CREATE INDEX IF NOT EXISTS deltas_address_idx ON deltas(address);
CREATE INDEX IF NOT EXISTS deltas_block_idx   ON deltas(block_number);
CREATE INDEX IF NOT EXISTS balances_balance_desc_idx ON balances (balance DESC, address ASC);
