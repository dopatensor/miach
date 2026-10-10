import type { ReactNode } from "react";

export function Card({ title, children, shadow = "#2E3F8F", className = "", aside, id }: {
  title?: ReactNode; children: ReactNode; shadow?: string; className?: string; aside?: ReactNode; id?: string;
}) {
  return (
    <section className={`card ${className}`} style={{ ["--shadow" as string]: shadow }} aria-labelledby={id}>
      {title && (
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 id={id} className="text-lg font-bold">{title}</h2>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}

export function Skeleton({ h = "h-32" }: { h?: string }) {
  return <div className={`skeleton w-full ${h}`} aria-hidden="true" />;
}

export function ErrorNote({ error }: { error: string }) {
  return <p role="alert" className="text-sm text-coralink">Could not load: {error}</p>;
}
