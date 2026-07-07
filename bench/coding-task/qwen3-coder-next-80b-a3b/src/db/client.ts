import { createClient } from "@libsql/client";

const client = createClient({
  url: process.env.DATABASE_URL || "file:./local.db",
});

export const db = client;
