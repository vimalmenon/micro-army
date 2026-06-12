export interface Message {
  id: string;
  name: string;
  email: string;
  subject: string;
  message: string;
  read: boolean;
  created_at: string;
  updated_at: string;
}

export interface StateTransition {
  state: string;
  at: string;
}

export interface Lead {
  id: string;
  source: string;
  url: string;
  title: string;
  company: string | null;
  score: number;
  pain_point: string;
  fit_reason: string;
  angle: string;
  urgency: string;
  state: string;
  seen_at: string;
  website: string | null;
  linkedin: string | null;
  contact_name: string | null;
  contact_email: string | null;
  recent_news: string[];
  tech_stack: string[];
  funding: string | null;
  budget_min: number | null;
  budget_max: number | null;
  budget_confidence: string | null;
  enriched_at: string | null;
  history: StateTransition[];
}

export type ViewState =
  | { tab: 'dashboard' }
  | { tab: 'messages' }
  | { tab: 'message-detail'; messageId: string }
  | { tab: 'leads' }
  | { tab: 'lead-detail'; leadId: string };