import type { ReactNode } from 'react';

function SectionHeader({
  eyebrow,
  title,
  description,
  action,
}: Readonly<{
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}>) {
  return (
    <div className="flex flex-col gap-3 border-b border-gray-800/80 px-5 py-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-cyan-400/80">{eyebrow}</p>
        <h2 className="mt-2 text-lg font-semibold text-white">{title}</h2>
        <p className="mt-1 max-w-2xl text-sm text-gray-400">{description}</p>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function DashboardSection({
  id,
  title,
  description,
  children,
  action,
}: Readonly<{
  id: string;
  title: string;
  description: string;
  children: ReactNode;
  action?: ReactNode;
}>) {
  return (
    <section id={id} className="overflow-hidden rounded-2xl border border-gray-800 bg-gray-900/45 shadow-[0_24px_80px_rgba(2,6,23,0.45)]">
      <SectionHeader eyebrow={id} title={title} description={description} action={action} />
      <div className="p-5">{children}</div>
    </section>
  );
}