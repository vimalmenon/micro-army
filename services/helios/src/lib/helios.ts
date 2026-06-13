import type { ViewState } from './types';

export const API_BASE = 'https://hestia.completeautomate.com';

export const LEAD_STATES = ['discovery', 'contacted', 'qualified', 'won', 'not_interested'];

export function formatTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return d.toLocaleDateString();
}

export function formatDate(iso: string): string {
  const d = new Date(iso);
  const month = d.toLocaleString('en-US', { month: 'short' });
  const day = d.getDate();
  const year = d.getFullYear();
  const hours = d.getHours().toString().padStart(2, '0');
  const mins = d.getMinutes().toString().padStart(2, '0');
  return `${month} ${day}, ${year} at ${hours}:${mins}`;
}

export function sourceIcon(source: string): string {
  switch (source) {
    case 'reddit': return '🤖';
    case 'hackernews': return '💬';
    case 'google_news': return '📰';
    case 'indeed': return '💼';
    case 'crunchbase': return '📊';
    case 'producthunt': return '🚀';
    default: return '📡';
  }
}

export function urgencyColor(urgency: string): string {
  switch (urgency) {
    case 'high': return 'text-red-400 bg-red-600/20';
    case 'medium': return 'text-yellow-400 bg-yellow-600/20';
    case 'low': return 'text-gray-400 bg-gray-600/20';
    default: return 'text-gray-500 bg-gray-600/10';
  }
}

export function stateColor(state: string): string {
  switch (state) {
    case 'discovery': return 'text-cyan-400 bg-cyan-600/20';
    case 'contacted': return 'text-blue-400 bg-blue-600/20';
    case 'qualified': return 'text-green-400 bg-green-600/20';
    case 'not_interested': return 'text-gray-500 bg-gray-600/20';
    case 'won': return 'text-yellow-400 bg-yellow-600/20';
    default: return 'text-gray-400 bg-gray-600/15';
  }
}

export function scoreColor(score: number): string {
  if (score >= 8) return 'text-green-400';
  if (score >= 5) return 'text-yellow-400';
  return 'text-gray-500';
}

export function getPageTitle(tab: ViewState['tab']): string {
  if (tab === 'dashboard') return 'Signals and sections';
  if (tab === 'messages' || tab === 'message-detail') return 'Inbox workspace';
  return 'Pipeline workspace';
}