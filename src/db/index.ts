import { drizzle } from 'drizzle-orm/node-postgres';
import { migrate } from 'drizzle-orm/node-postgres/migrator';
import { Pool } from 'pg';
import * as schema from './schema';

// Convert Python psycopg2 URL format to node-postgres format
const databaseUrl = process.env.DATABASE_URL?.replace('postgresql+psycopg2://', 'postgresql://') || '';

const pool = new Pool({
  connectionString: databaseUrl,
});

export const db = drizzle(pool, { schema });

// Auto-migrate on startup
export async function initializeDatabase() {
  try {
    await migrate(db, { migrationsFolder: './drizzle' });
    console.log('✅ Database initialized successfully');
  } catch (error) {
    console.error('❌ Database initialization failed:', error);
    throw error;
  }
}

export { schema };