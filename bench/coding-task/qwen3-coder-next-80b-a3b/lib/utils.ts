import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string | Date): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(date);
}

export function formatDateWithTime(dateString: string | Date): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function getPriorityColor(priority: string): string {
  const colors = {
    high: "bg-red-500",
    medium: "bg-yellow-500",
    low: "bg-green-500",
  };
  return colors[priority as keyof typeof colors] || "bg-gray-500";
}

export function getStatusColor(status: string): string {
  const colors = {
    pending: "bg-gray-500",
    in_progress: "bg-blue-500",
    completed: "bg-green-500",
  };
  return colors[status as keyof typeof colors] || "bg-gray-500";
}

export function generateId() {
  return Math.random().toString(36).substring(2, 9);
}
