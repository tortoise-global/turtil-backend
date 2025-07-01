import asyncpg
import asyncio

async def drop_tables():
    conn = await asyncpg.connect('postgresql://user:password@localhost:5432/turtil_db')
    
    # Get all table names
    tables = await conn.fetch("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename != 'alembic_version'
    """)
    
    print(f'Found {len(tables)} tables: {[t["tablename"] for t in tables]}')
    
    # Drop all tables with CASCADE to handle constraints
    for table in tables:
        table_name = table['tablename']
        try:
            await conn.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
            print(f'Dropped table: {table_name}')
        except Exception as e:
            print(f'Error dropping {table_name}: {e}')
    
    # Also drop alembic_version to reset migrations
    await conn.execute('DROP TABLE IF EXISTS alembic_version CASCADE')
    print('Dropped alembic_version table')
    
    await conn.close()
    print('All tables dropped successfully')

if __name__ == "__main__":
    asyncio.run(drop_tables())