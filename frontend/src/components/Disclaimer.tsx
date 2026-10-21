export function Disclaimer({ compact = false }: { compact?: boolean }) {
  if (compact) return <p className="text-[11px] text-mute">Research use only. Candidate panel; not for diagnosis or treatment decisions.</p>;
  return (
    <p className="text-[11px] text-mute">
      <span className="text-fg">Research use only.</span> Candidate biomarker panels for research, not validated
      diagnostics. Not for diagnosis or treatment decisions. All metrics are preliminary and are measured on locked
      test sets of TCGA tumours (breast panel: n = 176).
    </p>
  );
}
