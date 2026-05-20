import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { categories } from "@/db/schema";

export async function GET(request: NextRequest) {
  try {
    const categoriesData = await db.select().from(categories);

    return NextResponse.json({ success: true, data: categoriesData });
  } catch (error) {
    console.error("Error fetching categories:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch categories" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    const [newCategory] = await db
      .insert(categories)
      .values({
        name: data.name,
        description: data.description || null,
        color: data.color || "#6366f1",
      })
      .returning();

    return NextResponse.json({ success: true, data: newCategory }, { status: 201 });
  } catch (error) {
    console.error("Error creating category:", error);
    return NextResponse.json({ success: false, error: "Failed to create category" }, { status: 500 });
  }
}
