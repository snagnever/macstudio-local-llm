import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tasks, categories, taskTags, tags } from "@/db/schema";
import { eq, and, desc, asc, inArray, sql } from "drizzle-orm";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get("page") || "1");
    const limit = parseInt(searchParams.get("limit") || "10");
    const search = searchParams.get("search");
    const status = searchParams.get("status") as string;
    const priority = searchParams.get("priority") as string;
    const categoryId = parseInt(searchParams.get("category_id") || "");
    const tagId = parseInt(searchParams.get("tag_id") || "");
    const sortBy = searchParams.get("sort_by") || "created_at";
    const order = (searchParams.get("order") as "asc" | "desc") || "desc";

    const offset = (page - 1) * limit;

    let whereCondition = and();

    if (search) {
      whereCondition = and(whereCondition, eq(tasks.title, search));
    }
    if (status) {
      whereCondition = and(whereCondition, eq(tasks.status, status));
    }
    if (priority) {
      whereCondition = and(whereCondition, eq(tasks.priority, priority));
    }
    if (categoryId) {
      whereCondition = and(whereCondition, eq(tasks.category_id, categoryId));
    }

    const queryTasks = db
      .select({
        id: tasks.id,
        title: tasks.title,
        description: tasks.description,
        status: tasks.status,
        priority: tasks.priority,
        due_date: tasks.due_date,
        category_id: tasks.category_id,
        created_at: tasks.created_at,
        updated_at: tasks.updated_at,
      })
      .from(tasks)
      .where(whereCondition);

    if (tagId) {
      queryTasks.leftJoin(taskTags, eq(tasks.id, taskTags.task_id));
      queryTasks.where(eq(taskTags.tag_id, tagId));
    }

    if (sortBy === "due_date" && order === "asc") {
      queryTasks.orderBy(asc(tasks.due_date));
    } else if (sortBy === "due_date" && order === "desc") {
      queryTasks.orderBy(desc(tasks.due_date));
    } else if (sortBy === "created_at" && order === "asc") {
      queryTasks.orderBy(asc(tasks.created_at));
    } else if (sortBy === "created_at" && order === "desc") {
      queryTasks.orderBy(desc(tasks.created_at));
    } else if (sortBy === "priority" && order === "asc") {
      queryTasks.orderBy(asc(tasks.priority));
    } else if (sortBy === "priority" && order === "desc") {
      queryTasks.orderBy(desc(tasks.priority));
    } else {
      queryTasks.orderBy(desc(tasks.created_at));
    }

    const allTasks = await queryTasks;
    const totalTasks = await db.select({ count: db.count() }).from(tasks).where(whereCondition);

    const tasksWithRelations = await Promise.all(
      allTasks.map(async (task) => {
        const taskTagsData = await db
          .select({ tag_id: taskTags.tag_id })
          .from(taskTags)
          .where(eq(taskTags.task_id, task.id));

        const tagIds = taskTagsData.map((t) => t.tag_id);
        const taskTagsList = await db.select().from(tags).where(inArray(tags.id, tagIds));

        const category = task.category_id
          ? await db.select().from(categories).where(eq(categories.id, task.category_id))
          : null;

        return {
          ...task,
          category: category[0] || null,
          tags: taskTagsList,
        };
      })
    );

    return NextResponse.json({
      success: true,
      data: {
        tasks: tasksWithRelations,
        pagination: {
          page,
          limit,
          total: totalTasks[0]?.count || 0,
        },
      },
    });
  } catch (error) {
    console.error("Error fetching tasks:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch tasks" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { title, description, status, priority, due_date, category_id, tag_ids } = body;

    if (!title) {
      return NextResponse.json({ success: false, error: "Title is required" }, { status: 400 });
    }

    const newTask = await db
      .insert(tasks)
      .values({
        title,
        description: description || null,
        status: status || "pending",
        priority: priority || "medium",
        due_date: due_date || null,
        category_id: category_id || null,
      })
      .returning();

    const task = newTask[0];

    if (tag_ids && Array.isArray(tag_ids)) {
      await Promise.all(
        tag_ids.map((tagId: number) =>
          db.insert(taskTags).values({ task_id: task.id, tag_id: tagId })
        )
      );
    }

    const tagsList = await db.select().from(tags).where(inArray(tags.id, tag_ids || []));

    return NextResponse.json({
      success: true,
      data: { ...task, category: null, tags: tagsList },
    });
  } catch (error) {
    console.error("Error creating task:", error);
    return NextResponse.json({ success: false, error: "Failed to create task" }, { status: 500 });
  }
}
