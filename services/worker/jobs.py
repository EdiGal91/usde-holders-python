import os, requests, psycopg, redis
from rq import Queue
from typing import Dict, Any

ETHERSCAN_API_URL = os.environ["ETHERSCAN_API_URL"]
ETHERSCAN_API_KEY = os.environ["ETHERSCAN_API_KEY"]
USDE_ADDRESS = os.environ["USDE_ADDRESS"]
CONFIRMATIONS = int(os.environ["CONFIRMATIONS"])
DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
ZERO_ADDR = "0x" + "0" * 64  # indexed zero address in topics
OFFSET = 1000


r = redis.from_url(REDIS_URL)
q_parse_transfer = Queue("parse_transfer", connection=r)
q_calc_balance_by_transfers = Queue("calc_balance_by_transfers", connection=r)


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


def _topic_addr(topic_hex: str) -> bytes:
    return bytes.fromhex(topic_hex[-40:])


def _is_zero_topic(topic_hex: str) -> bool:
    return topic_hex.lower() in (ZERO_ADDR, "0x0")


def _hex_u256(data_hex: str) -> int:
    return int(data_hex, 16) if data_hex and data_hex != "0x" else 0


def parse_transfer(log: Dict[str, Any]):
    """Parse one ERC20 Transfer log and write deltas; enqueue balance updates."""
    print("[JOB] parse_transfer", log)

    try:
        bn = int(log["blockNumber"], 16)
        tx = log["transactionHash"]
        li = int(log["logIndex"], 16)
        topics = log.get("topics", [])
        if not topics or topics[0].lower() != TRANSFER_TOPIC:
            return  # not a Transfer
        if len(topics) < 3:
            return  # malformed

        from_topic = topics[1]
        to_topic = topics[2]
        amount = _hex_u256(log.get("data", "0x"))

        deltas = []
        addrs_for_balance = set()

        if not _is_zero_topic(from_topic):
            addr_from = _topic_addr(from_topic)
            deltas.append((bn, tx, li, addr_from, -amount))
            addrs_for_balance.add(addr_from)

        if not _is_zero_topic(to_topic):
            addr_to = _topic_addr(to_topic)
            deltas.append((bn, tx, li, addr_to, amount))
            addrs_for_balance.add(addr_to)

        if not deltas:
            return

        with psycopg.connect(DATABASE_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO deltas (block_number, tx_hash, log_index, address, amount)
                    VALUES (%s,%s,%s,%s,%s)
                    ON CONFLICT DO NOTHING
                    """,
                    deltas,
                )

        for addr in addrs_for_balance:
            q_calc_balance_by_transfers.enqueue(
                "jobs.calc_balance_by_transfers",
                addr.hex(),
                job_timeout=180,
                retry=None,
            )

    except Exception as e:
        print(f"[parse_transfer] error: {e}")
