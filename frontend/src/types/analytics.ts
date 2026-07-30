export interface StatusCount {
  status: string;
  count: number;
}

export interface PriorityCount {
  priority: string;
  count: number;
}

export interface WeeklyPoint {
  week_start: string;
  created: number;
  completed: number;
}

export interface WorkloadEntry {
  user_id: string;
  name: string;
  count: number;
}

export interface HandoverStats {
  pending: number;
  approved: number;
  rejected: number;
  avg_review_hours: number | null;
}

export interface Analytics {
  task_status: StatusCount[];
  task_priority: PriorityCount[];
  weekly: WeeklyPoint[];
  workload: WorkloadEntry[];
  handovers: HandoverStats;
}
