import os, json, base64
from contextlib import asynccontextmanager
from typing import Optional, Any, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool

DATABASE_URL = os.environ["DATABASE_URL"]


pool: AsyncConnectionPool


@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    pool = AsyncConnectionPool(
        DATABASE_URL, max_size=int(os.getenv("DB_POOL_SIZE", "10"))
    )
    await pool.open()
    try:
        yield
    finally:
        await pool.close()


app = FastAPI(title="USDe Holdings API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def _enc_cursor(balance: str, addr_bytes: bytes) -> str:
    payload = {"b": balance, "a": addr_bytes.hex()}
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def _dec_cursor(cursor: str):
    try:
        p = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
        return p["b"], bytes.fromhex(p["a"])
    except Exception:
        raise HTTPException(400, "Invalid cursor")


@app.get("/holders")
async def holders(limit: int = Query(50, ge=1, le=500), cursor: Optional[str] = None):
    where = ""
    params: List[Any] = []
    if cursor:
        last_balance_str, last_addr = _dec_cursor(cursor)
        where = (
            "WHERE (balance < %s::numeric) OR (balance = %s::numeric AND address > %s)"
        )
        params.extend([last_balance_str, last_balance_str, last_addr])

    sql = f"""
      SELECT address, balance
      FROM balances
      {where}
      ORDER BY balance DESC, address ASC
      LIMIT %s
    """
    params.append(limit)

    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(sql, params)
            rows = await cur.fetchall()

    items = [{"address": "0x" + r[0].hex(), "balance": str(r[1])} for r in rows]
    next_cursor = (
        _enc_cursor(str(rows[-1][1]), rows[-1][0])
        if rows and len(rows) == limit
        else None
    )
    return {"items": items, "next_cursor": next_cursor}


@app.get("/status")
async def status():
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT last_block FROM sync_state WHERE id=1")
            row = await cur.fetchone()
    return {"last_block": (row[0] if row else 0)}
