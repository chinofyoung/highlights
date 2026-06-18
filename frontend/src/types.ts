export interface Rally {
  start: number;
  end: number;
  confidence: number;
  serveStart: number;
  serveEnd: number;
  serveResolved: boolean;
  included: boolean;
}

export interface JobRecord {
  status: "running" | "done" | "error";
  progress: number;
  result: any;
  error: string | null;
}

export interface DetectParams {
  threshold?: number;
}

export interface Draft {
  video_id: string;
  original_filename: string;
  uploaded_at: number;
  analyzed: boolean;
  size_bytes: number;
}

export interface Project {
  video_id: string;
  original_filename: string;
  uploaded_at: number;
  size_bytes: number;
  clip_count: number;
}
