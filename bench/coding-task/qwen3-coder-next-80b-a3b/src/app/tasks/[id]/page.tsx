"use client";

import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TaskForm } from "@/components/tasks/TaskForm";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useState, useEffect } from "react";

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  const [task, setTask] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/tasks/${params.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && data.data) {
          setTask(data.data);
        }
        setLoading(false);
      });
  }, [params.id]);

  const handleSubmit = async (data: any) => {
    try {
      const response = await fetch(`/api/tasks/${params.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      });
      const result = await response.json();
      
      if (result.success) {
        window.location.href = "/tasks";
      }
    } catch (error) {
      console.error("Failed to update task:", error);
    }
  };

  const handleDelete = async () => {
    if (confirm("Are you sure you want to delete this task?")) {
      try {
        const response = await fetch(`/api/tasks/${params.id}`, { method: "DELETE" });
        if (response.ok) {
          window.location.href = "/tasks";
        }
      } catch (error) {
        console.error("Failed to delete task:", error);
      }
    }
  };

  if (loading) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold tracking-tight">Loading...</h1>
        </div>
      </DashboardLayout>
    );
  }

  if (!task) {
    return (
      <DashboardLayout>
        <div className="space-y-6">
          <h1 className="text-3xl font-bold tracking-tight">Task not found</h1>
          <Button asChild>
            <Link href="/tasks">Back to Tasks</Link>
          </Button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Edit Task</h1>
          <div className="flex gap-2">
            <Button variant="outline" asChild>
              <Link href="/tasks">Back</Link>
            </Button>
            <Button variant="destructive" onClick={handleDelete}>
              Delete
            </Button>
          </div>
        </div>

        <TaskForm
          defaultValues={{
            title: task.title,
            description: task.description || "",
            status: task.status,
            priority: task.priority,
            due_date: task.due_date ? new Date(task.due_date).toISOString().slice(0, 16) : "",
            category_id: task.category?.id || undefined,
          }}
          onSubmit={handleSubmit}
          submitText="Update Task"
        />
      </div>
    </DashboardLayout>
  );
}
