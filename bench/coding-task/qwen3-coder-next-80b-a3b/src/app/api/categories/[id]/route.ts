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

    const category = await db
      .select()
      .from(categories)
      .where(eq(categories.id, categoryId));

    if (!category[0]) {
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
    const data = await request.json();

    const existingCategory = await db.select().from(categories).where(eq(categories.id, categoryId));
    
    if (!existingCategory[0]) {
      return NextResponse.json({ success: false, error: "Category not found" }, { status: 404 });
    }

    const [updatedCategory] = await db
      .update(categories)
      .set({
        name: data.name,
        description: data.description !== undefined ? data.description : null,
        color: data.color || "#6366f1",
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

    const existingCategory = await db.select().from(categories).where(eq(categories.id, categoryId));
    
    if (!existingCategory[0]) {
      return NextResponse.json({ success: false, error: "Category not found" }, { status: 404 });
    }

    await db.delete(categories).where(eq(categories.id, categoryId));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting category:", error);
    return NextResponse.json({ success: false, error: "Failed to delete category" }, { status: 500 });
  }
}
