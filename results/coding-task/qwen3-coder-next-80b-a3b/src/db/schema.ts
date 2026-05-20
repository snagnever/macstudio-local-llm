import { integer, sqliteTable, text } from "drizzle-orm/sqlite-core";

export const categories = sqliteTable("categories", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  description: text("description"),
  color: text("color").default("#6366f1"),
  created_at: integer("created_at", { mode: "timestamp" }).$defaultFn(() => new Date()),
});

export const tags = sqliteTable("tags", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  name: text("name").notNull(),
  description: text("description"),
  created_at: integer("created_at", { mode: "timestamp" }).$defaultFn(() => new Date()),
});

export const tasks = sqliteTable("tasks", {
  id: integer("id").primaryKey({ autoIncrement: true }),
  title: text("title").notNull(),
  description: text("description"),
  status: text("status", { enum: ["pending", "in_progress", "completed"] }).default("pending"),
  priority: text("priority", { enum: ["low", "medium", "high"] }).default("medium"),
  due_date: integer("due_date", { mode: "timestamp" }),
  category_id: integer("category_id").references(() => categories.id),
  created_at: integer("created_at", { mode: "timestamp" }).$defaultFn(() => new Date()),
  updated_at: integer("updated_at", { mode: "timestamp" }).$defaultFn(() => new Date()),
});

export const taskTags = sqliteTable("task_tags", {
  task_id: integer("task_id").notNull().references(() => tasks.id, { onDelete: "cascade" }),
  tag_id: integer("tag_id").notNull().references(() => tags.id, { onDelete: "cascade" }),
  created_at: integer("created_at", { mode: "timestamp" }).$defaultFn(() => new Date()),
  PRIMARY_KEY: (sqliteTable) => [sqliteTable.task_id, sqliteTable.tag_id],
});
