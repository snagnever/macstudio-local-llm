import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tags } from "@/db/schema";

export async function GET(request: NextRequest) {
  try {
    const tagsData = await db.select().from(tags);

    return NextResponse.json({ success: true, data: tagsData });
  } catch (error) {
    console.error("Error fetching tags:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch tags" }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const data = await request.json();

    const [newTag] = await db
      .insert(tags)
      .values({
        name: data.name,
        description: data.description || null,
      })
      .returning();

    return NextResponse.json({ success: true, data: newTag }, { status: 201 });
  } catch (error) {
    console.error("Error creating tag:", error);
    return NextResponse.json({ success: false, error: "Failed to create tag" }, { status: 500 });
  }
}
