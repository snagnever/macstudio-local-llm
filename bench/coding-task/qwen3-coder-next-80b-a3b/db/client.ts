import { drizzle } from "drizzle-orm/better-sqlite3";
import Database from "better-sqlite3";

const sqlitePath = process.env.DATABASE_URL || "./db.sqlite";
const dbClient = new Database(sqlitePath);

export const db = drizzle(dbClient);
