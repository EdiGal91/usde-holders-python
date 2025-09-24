import os, requests, psycopg, redis
from rq import Queue

ETHERSCAN_API_URL = os.environ["ETHERSCAN_API_URL"]
ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
USDE_ADDRESS = os.environ["USDE_ADDRESS"]
CONFIRMATIONS = int(os.environ["CONFIRMATIONS"])
DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
OFFSET = 1000


r = redis.from_url(REDIS_URL)
q_parse_transfer = Queue("parse_transfer", connection=r)


def _get_last_block(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT last_block FROM sync_state WHERE id=1")
        row = cur.fetchone()
        if row is None:
            cur.execute("INSERT INTO sync_state(id,last_block) VALUES (1,0)")
            return 0
        result = int(row[0])
        print(f"_get_last_block result: {result}")
        return result


def _set_last_block(conn, b):
    print(f"_set_last_block to {b}")
    with conn.cursor() as cur:
        cur.execute("UPDATE sync_state SET last_block=%s WHERE id=1", (int(b),))


def _get_head():
    j = requests.get(
        ETHERSCAN_API_URL,
        params={
            "chainid": 1,
            "module": "proxy",
            "action": "eth_blockNumber",
            "apikey": ETHERSCAN_API_KEY,
        },
        timeout=10,
    ).json()
    return int(j["result"], 16)


def sync_transfers():
    print("[JOB] sync_transfers")
    with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
        last_block = _get_last_block(conn)
        head = _get_head()
        tip = head - CONFIRMATIONS

        print(f"sync_transfers last_block: {last_block}, tip: {tip}")
        resp = requests.get(
            ETHERSCAN_API_URL,
            params={
                "chainid": 1,
                "module": "logs",
                "action": "getLogs",
                "address": USDE_ADDRESS,
                "topic0": TRANSFER_TOPIC,
                "fromBlock": last_block,
                "toBlock": tip,
                "page": 1,
                "offset": OFFSET,
                "sort": "asc",
                "apikey": ETHERSCAN_API_KEY,
            },
            timeout=20,
        ).json()

        logs = resp.get("result", []) if resp.get("status") == "1" else []
        max_block = last_block

        for lg in logs:
            bn = int(lg["blockNumber"], 16)
            if bn > max_block:
                max_block = bn
            q_parse_transfer.enqueue(
                "jobs.parse_transfer",
                lg,
                job_timeout=180,
                retry=None,
            )

        new_last = tip if not logs else max_block
        if new_last > last_block:
            _set_last_block(conn, new_last)
