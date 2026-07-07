"use client";

import { Task } from "@/types";
import { TaskCard } from "./TaskCard";
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from "@/components/ui/pagination";
import { Button } from "@/components/ui/button";

interface TaskListProps {
  tasks: Task[];
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export function TaskList({ tasks, currentPage, totalPages, onPageChange }: TaskListProps) {
  if (tasks.length === 0) {
    return (
      <div className="text-center py-12">
        <h3 className="text-lg font-medium">No tasks found</h3>
        <p className="text-muted-foreground mt-2">Create a new task to get started</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} />
      ))}

      {totalPages > 1 && (
        <Pagination className="mt-8">
          <PaginationContent>
            <PaginationItem>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(Math.max(1, currentPage - 1))}
                disabled={currentPage === 1}
              >
                <PaginationPrevious />
              </Button>
            </PaginationItem>
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <PaginationItem key={page}>
                <Button
                  variant={currentPage === page ? "default" : "outline"}
                  size="sm"
                  onClick={() => onPageChange(page)}
                >
                  <PaginationLink isActive={currentPage === page}>{page}</PaginationLink>
                </Button>
              </PaginationItem>
            ))}
            <PaginationItem>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onPageChange(Math.min(totalPages, currentPage + 1))}
                disabled={currentPage === totalPages}
              >
                <PaginationNext />
              </Button>
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </div>
  );
}
