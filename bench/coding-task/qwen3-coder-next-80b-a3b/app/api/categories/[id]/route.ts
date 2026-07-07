import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { categories } from "@/db/schema";
import { eq } from "drizzle-orm";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const categoryId = parseInt(params.id);

    if (isNaN(categoryId)) {
      return NextResponse.json({ success: false, error: "Invalid category ID" }, { status: 400 });
    }

    const category = await db.select().from(categories).where(eq(categories.id, categoryId));

    if (category.length === 0) {
      return NextResponse.json({ success: false, error: "Category not found" }, { status: 404 });
    }

    return NextResponse.json({ success: true, data: category[0] });
  } catch (error) {
    console.error("Error fetching category:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch category" }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const categoryId = parseInt(params.id);

    if (isNaN(categoryId)) {
      return NextResponse.json({ success: false, error: "Invalid category ID" }, { status: 400 });
    }

    const existingCategory = await db.select().from(categories).where(eq(categories.id, categoryId));

    if (existingCategory.length === 0) {
      return NextResponse.json({ success: false, error: "Category not found" }, { status: 404 });
    }

    const body = await request.json();
    const { name, color } = body;

    const updatedCategory = await db
      .update(categories)
      .set({
        name: name || existingCategory[0].name,
        color: color || existingCategory[0].color,
      })
      .where(eq(categories.id, categoryId))
      .returning();

    return NextResponse.json({ success: true, data: updatedCategory[0] });
  } catch (error) {
    console.error("Error updating category:", error);
    return NextResponse.json({ success: false, error: "Failed to update category" }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const categoryId = parseInt(params.id);

    if (isNaN(categoryId)) {
      return NextResponse.json({ success: false, error: "Invalid category ID" }, { status: 400 });
    }

    const existingCategory = await db.select().from(categories).where(eq(categories.id, categoryId));

    if (existingCategory.length === 0) {
      return NextResponse.json({ success: false, error: "Category not found" }, { status: 404 });
    }

    await db.delete(categories).where(eq(categories.id, categoryId));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting category:", error);
    return NextResponse.json({ success: false, error: "Failed to delete category" }, { status: 500 });
  }
}
