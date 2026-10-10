import type { ReactNode } from "react";

export function Section({ title, children, className = "", aside, id, index }: {
  title?: ReactNode; children: ReactNode; className?: string; aside?: ReactNode; id?: string; index?: number;
}) {
  return (
    <section className={`section ${className}`} aria-labelledby={id}>
      {title && (
        <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id={id} className="label">
            {index != null && <span aria-hidden="true" className="mr-3 text-fg">{String(index).padStart(2, "0")}</span>}{title}
          </h2>
          {aside && <span className="text-[11px] text-mute">{aside}</span>}
        </div>
      )}
      {children}
    </section>
  );
}

export function Skeleton({ h = "h-32" }: { h?: string }) {
  return <div className={`skeleton ${h}`} aria-hidden="true" />;
}

export function ErrorNote({ error }: { error: string }) {
  return <p role="alert" className="text-warn">could not load: {error}</p>;
}

export function Dot({ subtype }: { subtype: string | null }) {
  return <span aria-hidden="true" className="mr-2 inline-block h-2 w-2 align-middle"
    style={{ background: `var(--c-${subtype ?? "Unknown"})` }} />;
}

export function TestSetTag({ n = 176 }: { n?: number }) {
  return <span>locked test · n = {n} · preliminary</span>;
}
