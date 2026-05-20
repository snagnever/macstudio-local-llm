import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { categories } from "@/db/schema";

export async function GET(request: NextRequest) {
  try {
    const categoriesList = await db.select().from(categories).orderBy(categories.created_at);

    return NextResponse.json({
      success: true,
      data: categoriesList,
    });
  } catch (error) {
    console.error("Error fetching categories:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch categories" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, color } = body;

    if (!name) {
      return NextResponse.json({ success: false, error: "Name is required" }, { status: 400 });
    }

    if (!color) {
      return NextResponse.json({ success: false, error: "Color is required" }, { status: 400 });
    }

    const newCategory = await db.insert(categories).values({ name, color }).returning();

    return NextResponse.json({
      success: true,
      data: newCategory[0],
    });
  } catch (error) {
    console.error("Error creating category:", error);
    return NextResponse.json({ success: false, error: "Failed to create category" }, { status: 500 });
  }
}
