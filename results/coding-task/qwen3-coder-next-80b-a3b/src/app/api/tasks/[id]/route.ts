import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tasks, categories } from "@/db/schema";
import { eq } from "drizzle-orm";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const taskId = parseInt(params.id);

    const task = await db
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
        category: {
          id: categories.id,
          name: categories.name,
          color: categories.color,
        },
      })
      .from(tasks)
      .leftJoin(categories, eq(tasks.category_id, categories.id))
      .where(eq(tasks.id, taskId));

    if (!task[0]) {
      return NextResponse.json({ success: false, error: "Task not found" }, { status: 404 });
    }

    return NextResponse.json({ success: true, data: task[0] });
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
    const data = await request.json();

    const existingTask = await db.select().from(tasks).where(eq(tasks.id, taskId));
    
    if (!existingTask[0]) {
      return NextResponse.json({ success: false, error: "Task not found" }, { status: 404 });
    }

    const [updatedTask] = await db
      .update(tasks)
      .set({
        title: data.title,
        description: data.description !== undefined ? data.description : null,
        status: data.status || "pending",
        priority: data.priority || "medium",
        due_date: data.due_date ? new Date(data.due_date) : null,
        category_id: data.category_id || null,
        updated_at: new Date(),
      })
      .where(eq(tasks.id, taskId))
      .returning();

    return NextResponse.json({ success: true, data: updatedTask[0] });
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

    const existingTask = await db.select().from(tasks).where(eq(tasks.id, taskId));
    
    if (!existingTask[0]) {
      return NextResponse.json({ success: false, error: "Task not found" }, { status: 404 });
    }

    await db.delete(tasks).where(eq(tasks.id, taskId));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting task:", error);
    return NextResponse.json({ success: false, error: "Failed to delete task" }, { status: 500 });
  }
}
