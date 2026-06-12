import { formatDate, formatTime } from '../lib/helios';
import type { Message } from '../lib/types';

export function MessageDetailPage({
  message,
  onBack,
  onMarkRead,
  onDelete,
}: Readonly<{
  message: Message;
  onBack: () => void;
  onMarkRead: (id: string) => void;
  onDelete: (id: string) => void;
}>) {
  return (
    <div className="space-y-6">
      <button
        onClick={onBack}
        className="flex items-center gap-2 text-sm text-gray-400 transition hover:text-gray-200"
      >
        ← Messages
      </button>

      <div className="rounded-xl border border-gray-800 bg-gray-900/60 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold">{message.subject}</h2>
            <p className="mt-1 text-sm text-gray-400">
              {message.name} &lt;{message.email}&gt;
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-right text-xs text-gray-500">
              <div>{formatTime(message.created_at)}</div>
              <div className="text-gray-600">{formatDate(message.created_at)}</div>
            </span>
            {!message.read && (
              <button
                onClick={() => onMarkRead(message.id)}
                className="rounded-md bg-cyan-600/20 px-3 py-1 text-xs font-medium text-cyan-400 transition hover:bg-cyan-600/30"
              >
                Mark Read
              </button>
            )}
            <button
              onClick={() => {
                if (globalThis.confirm('Delete this message?')) onDelete(message.id);
              }}
              className="rounded-md bg-red-600/20 px-3 py-1 text-xs font-medium text-red-400 transition hover:bg-red-600/30"
            >
              Delete
            </button>
          </div>
        </div>
        <div className="mt-6 whitespace-pre-wrap rounded-lg border border-gray-800 bg-gray-950/50 p-4 text-sm leading-7 text-gray-300">
          {message.message}
        </div>
      </div>
    </div>
  );
}