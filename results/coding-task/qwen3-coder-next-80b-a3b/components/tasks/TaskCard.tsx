"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { formatDate, getPriorityColor, getStatusColor } from "@/lib/utils";
import { Task } from "@/types";
import Link from "next/link";

interface TaskCardProps {
  task: Task;
}

export function TaskCard({ task }: TaskCardProps) {
  return (
    <Card className="w-full">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg font-semibold">{task.title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="pb-2">
        {task.description && (
          <p className="text-sm text-muted-foreground mb-2">{task.description}</p>
        )}
        <div className="flex flex-wrap gap-2 mb-3">
          <Badge variant="secondary" className={getStatusColor(task.status)}>
            {task.status.replace("_", " ")}
          </Badge>
          <Badge variant="secondary" className={getPriorityColor(task.priority)}>
            {task.priority}
          </Badge>
        </div>
        <div className="flex justify-between items-center">
          {task.due_date && (
            <span className="text-xs text-muted-foreground">
              Due: {formatDate(task.due_date)}
            </span>
          )}
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/tasks/${task.id}`}>View</Link>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
