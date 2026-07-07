import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function TagsPage() {
  const tags = [];

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Tags</h1>
          <Button>Create Tag</Button>
        </div>

        {tags.length === 0 ? (
          <Card>
            <CardContent className="py-12 text-center">
              <p className="text-muted-foreground">No tags yet</p>
            </CardContent>
          </Card>
        ) : (
          <div className="flex flex-wrap gap-2">
            {tags.map((tag: any) => (
              <Card key={tag.id} className="flex items-center gap-2 px-4 py-2">
                <CardTitle>{tag.name}</CardTitle>
              </Card>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  );
}
