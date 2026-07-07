import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tasks, categories, taskTags, tags } from "@/db/schema";
import { eq, and, desc, asc, inArray, sql } from "drizzle-orm";

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    const page = parseInt(searchParams.get("page") || "1");
    const limit = parseInt(searchParams.get("limit") || "10");
    const search = searchParams.get("search") || "";
    const statusFilter = searchParams.get("status");
    const priorityFilter = searchParams.get("priority");
    const categoryId = searchParams.get("category_id");

    let whereConditions = [];
    
    if (search) {
      whereConditions.push(sql`tasks.title LIKE ${'%' + search + '%'}`);
    }
    
    if (statusFilter && statusFilter !== "all") {
      whereConditions.push(eq(tasks.status, statusFilter));
    }
    
    if (priorityFilter && priorityFilter !== "all") {
      whereConditions.push(eq(tasks.priority, priorityFilter));
    }
    
    if (categoryId && categoryId !== "all") {
      whereConditions.push(eq(tasks.category_id, parseInt(categoryId)));
    }

    const whereClause = whereConditions.length > 0 ? and(...whereConditions) : undefined;

    const offset = (page - 1) * limit;
    
    const whereResult = whereConditions.length > 0 ? and(...whereConditions) : undefined;
    
    const tasksData = await db
      .select({
        id: tasks.id,
        title: tasks.title,
        description: tasks.description,
        status: tasks.status,
        priority: tasks.priority,
        due_date: tasks.due_date,
        category_id: tasks.category_id,
        created_at: tasks.created_at,
        category: {
          id: categories.id,
          name: categories.name,
          color: categories.color,
        },
      })
      .from(tasks)
      .leftJoin(categories, eq(tasks.category_id, categories.id))
      .where(whereResult)
      .orderBy(desc(tasks.created_at))
      .limit(limit)
      .offset(offset);

    const [{ count }] = await db
      .select({ count: sql`count(*)`.as("count") })
      .from(tasks)
      .where(whereResult);

    return NextResponse.json({
      success: true,
      data: tasksData,
      pagination: {
        total: Number(count),
        page,
        limit,
        totalPages: Math.ceil(Number(count) / limit),
      },
    });
  } catch (error) {
    console.error("Error fetching tasks:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch tasks" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    const [newTask] = await db
      .insert(tasks)
      .values({
        title: data.title,
        description: data.description || null,
        status: data.status || "pending",
        priority: data.priority || "medium",
        due_date: data.due_date ? new Date(data.due_date) : null,
        category_id: data.category_id || null,
      })
      .returning();

    return NextResponse.json({ success: true, data: newTask }, { status: 201 });
  } catch (error) {
    console.error("Error creating task:", error);
    return NextResponse.json({ success: false, error: "Failed to create task" }, { status: 500 });
  }
}
