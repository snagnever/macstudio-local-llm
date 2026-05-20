import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tags } from "@/db/schema";

export async function GET(request: NextRequest) {
  try {
    const tagsList = await db.select().from(tags).orderBy(tags.created_at);

    return NextResponse.json({
      success: true,
      data: tagsList,
    });
  } catch (error) {
    console.error("Error fetching tags:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch tags" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name } = body;

    if (!name) {
      return NextResponse.json({ success: false, error: "Name is required" }, { status: 400 });
    }

    const newTag = await db.insert(tags).values({ name }).returning();

    return NextResponse.json({
      success: true,
      data: newTag[0],
    });
  } catch (error) {
    console.error("Error creating tag:", error);
    return NextResponse.json({ success: false, error: "Failed to create tag" }, { status: 500 });
  }
}
