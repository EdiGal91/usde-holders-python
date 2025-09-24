#!/usr/bin/env bash
set -e
psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 -c "\i schema.sql"
rq worker -u "${REDIS_URL}" sync_transfers calc_balance_by_transfers parse_transfer