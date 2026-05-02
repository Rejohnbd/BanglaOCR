export interface VoterFieldStatus {
  sl: boolean;
  name: boolean;
  voter_no: boolean;
  father_name: boolean;
  mother_name: boolean;
  occupation: boolean;
  date_of_birth_bangla: boolean;
  date_of_birth_eng: boolean;
  address: boolean;
}

export interface VoterData {
  sl: string;
  name: string;
  voter_no: string;
  father_name: string;
  mother_name: string;
  occupation: string;
  date_of_birth_bangla: string;
  date_of_birth_eng: string;
  address: string;
  full_text: string;
  status: boolean;
  fields: VoterFieldStatus;
  _source_page: number;
  _source_cell: number;
}

export interface DebugImage {
  name: string;
  page: string;
  url: string;
}

export interface FileInfo {
  name: string | null;
  exists: boolean;
  size_bytes: number;
  url: string | null;
}

export interface SummaryData {
  total_voters: number;
  total_pages: number;
  total_voters_expected: number;
  success_rate: string;
  extraction_time_seconds: number;
}

export interface DownloadResponse {
  task_id: string;
  status: string;
  created_at: string | null;
  completed_at: string | null;
  file: FileInfo;
  debug_grids: DebugImage[];
  data: VoterData[];
  summary: SummaryData;
}

// 🔥 আপডেটেড TaskStatus - নতুন ফিল্ড যোগ করা হয়েছে
export interface TaskStatus {
  task_id: string;
  engine: string;
  status: 'processing' | 'completed' | 'failed' | 'pending';
  total_voters: number;
  total_page: number;
  current_page: number;
  progress_percent: number;
  created_at: string | null;
  completed_at: string | null;
  error: string | null;
  download_url: string | null;
  debug_url: string | null;
}

// 🔥 নতুন Error Response টাইপ
export interface ErrorResponse {
  error: string;
  task_id: string;
  message: string;
}

export interface UploadResponse {
  task_id: string;
  status_url: string;
  download_url: string;
  debug_url: string;
}
