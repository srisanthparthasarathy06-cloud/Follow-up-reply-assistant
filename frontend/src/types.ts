export interface EmailOut {
  id: string;
  sender: string;
  subject: string;
  body: string;
  status: string;
  priority: string | null;
  intent: string | null;
  tone: string | null;
  summary: string | null;
  received_at: string;
  reply_count: number;
}

export interface EmailAnalysis {
  intent: string;
  priority: string;
  tone: string;
  urgency: string;
  sentiment: string;
  required_action: string;
  questions_asked: string[];
  key_entities: string[];
  relevant_dates: string[];
  known_information: string[];
  missing_information: string[];
  summary: string;
}

export interface ReplyOut {
  id: string;
  style: string;
  body: string;
  is_selected: boolean;
  was_edited: boolean;
  was_sent: boolean;
}

export interface GenerateRepliesResponse {
  email_id: string;
  analysis: EmailAnalysis;
  replies: ReplyOut[];
}

export interface BulkJobOut {
  id: string;
  total: number;
  processed: number;
  succeeded: number;
  failed: number;
  status: string;
  failed_email_ids: string[];
}

export interface AnalyticsOut {
  emails_processed_per_day: Record<string, number>;
  replies_generated: number;
  replies_sent: number;
  avg_processing_time_seconds: number;
  top_intents: Record<string, number>;
  top_reply_styles: Record<string, number>;
  success_rate: number;
}

export interface EmailAccountOut {
  id: string;
  provider: string;
  email_address: string;
  connected_at: string;
}

export interface SyncResponse {
  fetched: number;
  added: number;
  skipped_duplicates: number;
}
