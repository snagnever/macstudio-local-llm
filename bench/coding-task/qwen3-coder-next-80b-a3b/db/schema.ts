import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

export const categories = sqliteTable("categories", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull().unique(),
  color: text("color").notNull(),
  created_at: text("created_at").default("datetime('now')"),
});

export const tags = sqliteTable("tags", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull().unique(),
});

export const tasks = sqliteTable("tasks", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status", { enum: ["pending", "in_progress", "completed"] }).notNull().default("pending"),
  priority: text("priority", { enum: ["low", "medium", "high"] }).notNull().default("medium"),
  due_date: text("due_date"),
  category_id: integer("category_id").references(() => categories.id),
  created_at: text("created_at").default("datetime('now')"),
  updated_at: text("updated_at").default("datetime('now')"),
});

export const taskTags = sqliteTable("task_tags", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  task_id: integer("task_id").notNull().references(() => tasks.id, { onDelete: "cascade" }),
  tag_id: integer("tag_id").notNull().references(() => tags.id, { onDelete: "cascade" }),
});
