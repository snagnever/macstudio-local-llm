import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { TaskList } from "@/components/tasks/TaskList";
import { TaskFilters } from "@/components/tasks/TaskFilters";
import { Button } from "@/components/ui/button";
import Link from "next/link";

export default function TasksPage() {
  const tasks = [];
  const currentPage = 1;
  const totalPages = 0;

  return (
    <DashboardLayout>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold tracking-tight">Tasks</h1>
          <Button asChild>
            <Link href="/tasks/new">Create Task</Link>
          </Button>
        </div>

        <TaskFilters
          searchQuery=""
          onSearchChange={() => {}}
          statusFilter={null}
          onStatusChange={() => {}}
          priorityFilter={null}
          onPriorityChange={() => {}}
          clearFilters={() => {}}
        />

        <TaskList
          tasks={tasks}
          currentPage={currentPage}
          totalPages={totalPages}
          onPageChange={() => {}}
        />
      </div>
    </DashboardLayout>
  );
}
