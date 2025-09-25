# USDe Holdings Tracker (Worker + Scheduler)

Tracks **USDe** ERC-20 transfers on Ethereum, stores **deltas** and maintains **per-address balances**.  
Built with **Python**, **RQ**/**rq-scheduler**, **PostgreSQL**, **Redis**, and **Docker Compose**.

## Overview

**Services**

- **Postgres** – data store.
- **Redis** – queues + scheduler storage.
- **Worker** – runs RQ worker listening to queues.
- **Scheduler** – enqueues periodic jobs (every 15s by default).

**Queues**

1. `sync_transfers` – periodic trigger (scheduler calls).
2. `parse_transfer` – parses one raw log → writes 2 deltas (+to / −from) → enqueues balance updates.
3. `calc_balance` (planned) – recomputes balance for one address.

**Database tables**

- `sync_state(id SMALLINT PRIMARY KEY, last_block BIGINT NOT NULL)` – sync cursor (last fully processed block).
- `deltas(block_number BIGINT, tx_hash TEXT, log_index INT, address BYTEA, amount NUMERIC(78,0), PRIMARY KEY(block_number, tx_hash, log_index, address))`
- `balances(address BYTEA PRIMARY KEY, balance NUMERIC(78,0) NOT NULL)`

**Idempotency**

- `deltas` PK prevents duplicates.
- Balances recomputed per address (UPSERT).

---

## Prerequisites

- Docker & Docker Compose installed.

---

## Environment

Create a `.env` in repo root:

```env
POSTGRES_USER=pg
POSTGRES_PASSWORD=pg
POSTGRES_DB=usde
DATABASE_URL=postgresql://pg:pg@postgres:5432/usde

REDIS_URL=redis://redis:6379

ETHERSCAN_API_URL=https://api.etherscan.io/v2/api
ETHERSCAN_API_KEY=YOUR_ETHERSCAN_KEY

USDE_ADDRESS=0x4c9edd5852cd905f086c759e8383e09bff1e68b3
CONFIRMATIONS=12
```

> The compose file reads this `.env` via `env_file`.

---

## One-time setup

Make the worker entrypoint executable:

```bash
chmod +x services/worker/run.sh
```

---

## Run (Docker)

Build & start all services (example scales workers to 16):

```bash
docker compose up -d --build --scale worker=16
```

Tail logs:

```bash
# worker logs (all replicas)
docker compose logs -f worker

# scheduler logs
docker compose logs -f scheduler

# postgres / redis
docker compose logs -f postgres
docker compose logs -f redis
```

Stop services (keep data volumes):

```bash
docker compose down
```

Stop **and delete** volumes (reset DB/Redis data):

```bash
docker compose down -v
```

> Use `-v` when you want a **clean slate** (e.g., reset `last_block` to 0).

Rebuild after code changes (worker/scheduler):

```bash
docker compose up -d --build
```

---

## Monitoring Queues and Jobs

We use [RQ Dashboard](https://github.com/Parallels/rq-dashboard) to monitor queues, workers, and jobs.

### Start Dashboard

```bash
docker compose up -d rqdashboard
```

Open http://localhost:9181 in your browser.

Default login credentials:

- Username: admin
- Password: admin

## Postgres access

Open a psql shell:

```bash
docker exec -it usde_tracker_postgres psql -U pg -d usde
```

Reset sync cursor only (without dropping volumes):

```sql
TRUNCATE sync_state;
INSERT INTO sync_state(id, last_block) VALUES (1, 0);
```

---

## How it works (flow)

1. **Scheduler** (rq-scheduler) enqueues `jobs.sync_transfers` into queue `sync_transfers` every 15s.
2. **sync_transfers**:
   - Reads `last_block` from `sync_state`.
   - Gets `head` via `module=proxy&action=eth_blockNumber`.
   - Sets `tip = head - CONFIRMATIONS`.
   - Pulls **one page** of ERC-20 `Transfer` logs (`module=logs&action=getLogs`, `topic0=Transfer`, `fromBlock=last_block+1` to `tip`).
   - Enqueues **each raw log** to queue `parse_transfer`.
   - Advances `last_block` to `max_block_seen` (or to `tip` if empty).
3. **parse_transfer** (to implement in `jobs.py`):
   - Parses `topics` and `data` → `from`, `to`, `amount`.
   - Inserts two rows into `deltas` (idempotent PK).
   - Enqueues `calc_balance(address)` for both addresses (with Redis SET or DB guard to dedupe).
4. **calc_balance** (optional first version = full recompute):
   - `new = COALESCE(SUM(amount) FROM deltas WHERE address=?, 0)`.
   - `UPSERT` into `balances`.

---

## Common commands

Recreate just worker container:

```bash
docker compose -f infra/compose.yml up -d --build worker
```

Recreate just scheduler container:

```bash
docker compose -f infra/compose.yml up -d --build scheduler
```

Show containers:

```bash
docker ps
```

Remove dangling images (optional cleanup):

```bash
docker image prune -f
```

---

## Config knobs

- `CONFIRMATIONS` – how many blocks to wait before considering logs final (e.g., `12`).
- `OFFSET` (in code) – max logs per page (we use `1000` and **no pagination**).
- Scheduling interval – set in `services/worker/schedule.py`:
  - `interval=15` seconds in `sch.schedule(...)`.
  - rqscheduler poll interval is set via container args (e.g., `-i 1`).

---

## Troubleshooting

- **Cursor didn’t reset after removing containers**  
  Use `down -v` to remove **volumes** or truncate `sync_state` as above.
- **429 / API errors**  
  Add small backoff or lower schedule frequency. Check Etherscan key quota.
- **`psql: command not found` inside worker**  
  The schema is applied from the worker container; ensure `psql` is installed there (already handled in Dockerfile).

---

## Next steps

- Implement `jobs.parse_transfer` and `jobs.calc_balance`.
- Add a lightweight HTTP API (FastAPI) to serve balances.
- Add basic dashboard (optional).

---

**License:** MIT (or your choice).
