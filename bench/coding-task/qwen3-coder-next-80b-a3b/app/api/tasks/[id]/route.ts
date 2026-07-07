import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tasks, categories, taskTags, tags } from "@/db/schema";
import { eq, inArray } from "drizzle-orm";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const taskId = parseInt(params.id);

    if (isNaN(taskId)) {
      return NextResponse.json({ success: false, error: "Invalid task ID" }, { status: 400 });
    }

    const task = await db.select().from(tasks).where(eq(tasks.id, taskId));

    if (task.length === 0) {
      return NextResponse.json({ success: false, error: "Task not found" }, { status: 404 });
    }

    const taskWithDetails = task[0];

    const taskTagsData = await db
      .select({ tag_id: taskTags.tag_id })
      .from(taskTags)
      .where(eq(taskTags.task_id, taskId));

    const tagIds = taskTagsData.map((t) => t.tag_id);
    const tagsList = await db.select().from(tags).where(inArray(tags.id, tagIds));

    const category = taskWithDetails.category_id
      ? await db.select().from(categories).where(eq(categories.id, taskWithDetails.category_id))
      : null;

    return NextResponse.json({
      success: true,
      data: { ...taskWithDetails, category: category[0] || null, tags: tagsList },
    });
  } catch (error) {
    console.error("Error fetching task:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch task" }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const taskId = parseInt(params.id);

    if (isNaN(taskId)) {
      return NextResponse.json({ success: false, error: "Invalid task ID" }, { status: 400 });
    }

    const existingTask = await db.select().from(tasks).where(eq(tasks.id, taskId));

    if (existingTask.length === 0) {
      return NextResponse.json({ success: false, error: "Task not found" }, { status: 404 });
    }

    const body = await request.json();
    const { title, description, status, priority, due_date, category_id, tag_ids } = body;

    const updatedTask = await db
      .update(tasks)
      .set({
        title: title || existingTask[0].title,
        description: description !== undefined ? description : existingTask[0].description,
        status: status || existingTask[0].status,
        priority: priority || existingTask[0].priority,
        due_date: due_date !== undefined ? due_date : existingTask[0].due_date,
        category_id: category_id !== undefined ? category_id : existingTask[0].category_id,
      })
      .where(eq(tasks.id, taskId))
      .returning();

    if (tag_ids !== undefined && Array.isArray(tag_ids)) {
      await db.delete(taskTags).where(eq(taskTags.task_id, taskId));
      await Promise.all(
        tag_ids.map((tagId: number) =>
          db.insert(taskTags).values({ task_id: taskId, tag_id: tagId })
        )
      );
    }

    const tagsList = await db.select().from(tags).where(inArray(tags.id, tag_ids || []));

    return NextResponse.json({
      success: true,
      data: { ...updatedTask[0], category: null, tags: tagsList },
    });
  } catch (error) {
    console.error("Error updating task:", error);
    return NextResponse.json({ success: false, error: "Failed to update task" }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const taskId = parseInt(params.id);

    if (isNaN(taskId)) {
      return NextResponse.json({ success: false, error: "Invalid task ID" }, { status: 400 });
    }

    const existingTask = await db.select().from(tasks).where(eq(tasks.id, taskId));

    if (existingTask.length === 0) {
      return NextResponse.json({ success: false, error: "Task not found" }, { status: 404 });
    }

    await db.delete(taskTags).where(eq(taskTags.task_id, taskId));
    await db.delete(tasks).where(eq(tasks.id, taskId));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting task:", error);
    return NextResponse.json({ success: false, error: "Failed to delete task" }, { status: 500 });
  }
}
