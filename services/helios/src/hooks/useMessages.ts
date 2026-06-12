import { useCallback, useEffect, useState } from 'react';

import { API_BASE } from '../lib/helios';
import type { Message } from '../lib/types';

export function useMessages() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchMessages = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(`${API_BASE}/messages`, {
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setMessages(data.messages);
      setUnreadCount(data.messages.filter((message: Message) => !message.read).length);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load messages');
    }
    setLoading(false);
  }, []);

  useEffect(() => { fetchMessages(); }, [fetchMessages]);

  const markRead = async (id: string) => {
    try {
      const resp = await fetch(`${API_BASE}/messages/${id}/read`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setMessages((prev) =>
        prev.map((message) => (message.id === id ? { ...message, read: true } : message))
      );
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (e) {
      console.error('Failed to mark as read', e);
    }
  };

  const deleteMessage = async (id: string) => {
    try {
      const resp = await fetch(`${API_BASE}/messages/${id}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      setMessages((prev) => prev.filter((message) => message.id !== id));
      setUnreadCount((count) => Math.max(0, count - 1));
    } catch (e) {
      console.error('Failed to delete message', e);
    }
  };

  return { messages, loading, error, unreadCount, fetchMessages, markRead, deleteMessage };
}