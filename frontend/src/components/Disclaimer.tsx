export function Disclaimer({ compact = false }: { compact?: boolean }) {
  if (compact)
    return (
      <p className="text-xs text-ink/80">
        <strong>Research use only.</strong> Candidate panel; not for diagnosis or treatment decisions.
      </p>
    );
  return (
    <p className="text-sm">
      <strong>Research use only.</strong> Miach outputs candidate biomarker panels for research. They are not
      validated diagnostics and must not be used for diagnosis or treatment decisions. All metrics are{" "}
      <strong>preliminary</strong> and come from a single locked test set of TCGA breast tumours.
    </p>
  );
}
