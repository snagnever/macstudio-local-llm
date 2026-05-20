"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TaskForm } from "@/components/tasks/TaskForm";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function NewTaskPage() {
  const handleSubmit = async (data: any) => {
    try {
      const response = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      
      if (result.success) {
        window.location.href = "/tasks";
      }
    } catch (error) {
      console.error("Failed to create task:", error);
    }
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Create New Task</h1>
          <Button variant="outline" asChild>
            <Link href="/tasks">Cancel</Link>
          </Button>
        </div>

        <TaskForm onSubmit={handleSubmit} submitText="Create Task" />
      </div>
    </DashboardLayout>
  );
}
