export function Disclaimer({ compact = false }: { compact?: boolean }) {
  if (compact) return <p className="text-[11px] text-mute">Research use only. Candidate panel; not for diagnosis or treatment decisions.</p>;
  return (
    <p className="text-[11px] text-mute">
      <span className="text-fg">Research use only.</span> Candidate biomarker panels for research, not validated
      diagnostics. Not for diagnosis or treatment decisions. All metrics are preliminary and come from one locked
      test set of TCGA breast tumours (n = 176).
    </p>
  );
}
