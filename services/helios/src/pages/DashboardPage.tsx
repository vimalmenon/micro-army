import { useHeliosData } from '../context/HeliosDataContext';
import { DashboardSection } from '../components/DashboardSection';
import { LeadsPage } from './LeadsPage';
import { MessagesPage } from './MessagesPage';

function OverviewSection({
  messageCount,
  unreadCount,
  leadCount,
  hotCount,
  warmCount,
}: Readonly<{
  messageCount: number;
  unreadCount: number;
  leadCount: number;
  hotCount: number;
  warmCount: number;
}>) {
  const stats = [
    { label: 'Total Messages', value: messageCount, tone: 'text-white' },
    { label: 'Unread Inbox', value: unreadCount, tone: 'text-cyan-400' },
    { label: 'Lead Pipeline', value: leadCount, tone: 'text-white' },
    { label: 'Hot Leads', value: hotCount, tone: 'text-green-400' },
    { label: 'Warm Leads', value: warmCount, tone: 'text-yellow-400' },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="rounded-2xl border border-gray-800/80 bg-gray-950/60 p-4"
        >
          <p className={`text-3xl font-semibold ${stat.tone}`}>{stat.value}</p>
          <p className="mt-2 text-xs uppercase tracking-[0.18em] text-gray-500">{stat.label}</p>
        </div>
      ))}
    </div>
  );
}

export function DashboardPage() {
  const { messages, leads, unreadCount, hotCount, warmCount } = useHeliosData();

  return (
    <div className="space-y-6">
      <div className="grid gap-3 rounded-2xl border border-gray-800 bg-gray-900/45 p-4 md:grid-cols-3">
        {[
          { label: 'Overview', href: '#overview' },
          { label: 'Inbox', href: '#messages' },
          { label: 'Pipeline', href: '#leads' },
        ].map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="rounded-xl border border-gray-800 bg-gray-950/60 px-4 py-3 text-sm text-gray-300 transition hover:border-cyan-500/40 hover:text-white"
          >
            {item.label}
          </a>
        ))}
      </div>

      <DashboardSection
        id="overview"
        title="Signal overview"
        description="A single scan of inbox volume, pipeline pressure, and lead temperature."
      >
        <OverviewSection
          messageCount={messages.length}
          unreadCount={unreadCount}
          leadCount={leads.length}
          hotCount={hotCount}
          warmCount={warmCount}
        />
      </DashboardSection>

      <MessagesPage
        messages={messages.slice(0, 5)}
      />

      <LeadsPage
        leads={leads.slice(0, 6)}
      />
    </div>
  );
}