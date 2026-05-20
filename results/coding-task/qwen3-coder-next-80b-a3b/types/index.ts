export type Priority = "low" | "medium" | "high";
export type Status = "pending" | "in_progress" | "completed";

export interface Category {
  id: number;
  name: string;
  color: string;
  created_at: string;
}

export interface Tag {
  id: number;
  name: string;
}

export interface Task {
  id: number;
  title: string;
  description?: string | null;
  status: Status;
  priority: Priority;
  due_date?: string | null;
  category_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskWithRelations extends Task {
  category?: Category | null;
  tags: Tag[];
}

export interface FilterParams {
  search?: string;
  status?: Status;
  priority?: Priority;
  category_id?: number;
  tag_id?: number;
  sort_by?: string;
  order?: "asc" | "desc";
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
}
