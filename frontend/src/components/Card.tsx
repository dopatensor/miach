import type { ReactNode } from "react";

export function Section({ title, children, className = "", aside, id, index }: {
  title?: ReactNode; children: ReactNode; className?: string; aside?: ReactNode; id?: string; index?: number;
}) {
  return (
    <section className={`section ${className}`} aria-labelledby={id}>
      {title && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-2">
          <h2 id={id} className="label flex items-center">
            {index != null && (
              <span aria-hidden="true" className="mr-3 inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-accsoft px-1.5 text-[11px] text-acc">
                {String(index).padStart(2, "0")}
              </span>
            )}{title}
          </h2>
          {aside && <span className="chip font-mono text-xs text-mute">{aside}</span>}
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
  return <span aria-hidden="true" className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
    style={{ background: `var(--c-${subtype ?? "Unknown"})` }} />;
}

export function TestSetTag({ n = 176 }: { n?: number }) {
  return <span>locked test · n = {n} · preliminary</span>;
}
