import { NextRequest, NextResponse } from "next/server";
import { db } from "@/db/client";
import { tags } from "@/db/schema";
import { eq } from "drizzle-orm";

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const tagId = parseInt(params.id);

    const tag = await db
      .select()
      .from(tags)
      .where(eq(tags.id, tagId));

    if (!tag[0]) {
      return NextResponse.json({ success: false, error: "Tag not found" }, { status: 404 });
    }

    return NextResponse.json({ success: true, data: tag[0] });
  } catch (error) {
    console.error("Error fetching tag:", error);
    return NextResponse.json({ success: false, error: "Failed to fetch tag" }, { status: 500 });
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const tagId = parseInt(params.id);
    const data = await request.json();

    const existingTag = await db.select().from(tags).where(eq(tags.id, tagId));
    
    if (!existingTag[0]) {
      return NextResponse.json({ success: false, error: "Tag not found" }, { status: 404 });
    }

    const [updatedTag] = await db
      .update(tags)
      .set({
        name: data.name,
        description: data.description !== undefined ? data.description : null,
      })
      .where(eq(tags.id, tagId))
      .returning();

    return NextResponse.json({ success: true, data: updatedTag[0] });
  } catch (error) {
    console.error("Error updating tag:", error);
    return NextResponse.json({ success: false, error: "Failed to update tag" }, { status: 500 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const tagId = parseInt(params.id);

    const existingTag = await db.select().from(tags).where(eq(tags.id, tagId));
    
    if (!existingTag[0]) {
      return NextResponse.json({ success: false, error: "Tag not found" }, { status: 404 });
    }

    await db.delete(tags).where(eq(tags.id, tagId));

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Error deleting tag:", error);
    return NextResponse.json({ success: false, error: "Failed to delete tag" }, { status: 500 });
  }
}
