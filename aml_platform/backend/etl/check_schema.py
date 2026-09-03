import asyncio
import os

import asyncpg

async def run():
    # DSN (including credentials) comes exclusively from the environment.
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'alerts'")
    print([r[0] for r in rows])
    await conn.close()

asyncio.run(run())
