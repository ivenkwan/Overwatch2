import asyncio
import asyncpg

async def run():
    conn = await asyncpg.connect('postgresql://aml_api_role:aml_secure_api_password@localhost:5433/age_prod_01')
    rows = await conn.fetch("SELECT column_name FROM information_schema.columns WHERE table_schema = 'app' AND table_name = 'alerts'")
    print([r[0] for r in rows])
    await conn.close()

asyncio.run(run())
