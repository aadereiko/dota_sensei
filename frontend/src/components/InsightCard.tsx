import type { Insight, Severity } from "@/types";

const SEVERITY_STYLES: Record<Severity, string> = {
  critical: "border-loss/60 bg-loss/10",
  warn: "border-warn/60 bg-warn/10",
  info: "border-border-subtle bg-surface-raised",
};

const SEVERITY_LABELS: Record<Severity, string> = {
  critical: "fix this",
  warn: "watch it",
  info: "note",
};

export function InsightCard({ insight }: { insight: Insight }) {
  return (
    <article className={`rounded-lg border p-4 ${SEVERITY_STYLES[insight.severity]}`}>
      <header className="flex items-start justify-between gap-3">
        <h3 className="font-medium text-slate-100">{insight.title}</h3>
        <span className="shrink-0 rounded-full border border-border-subtle px-2 py-0.5 text-xs uppercase tracking-wide text-slate-400">
          {SEVERITY_LABELS[insight.severity]}
        </span>
      </header>
      <p className="mt-2 text-sm leading-relaxed text-slate-300">{insight.detail}</p>
      {insight.metrics && Object.keys(insight.metrics).length > 0 && (
        <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-400">
          {Object.entries(insight.metrics).map(([key, value]) => (
            <div key={key} className="flex gap-1.5">
              <dt>{key.replaceAll("_", " ")}</dt>
              <dd className="font-mono text-slate-200">{String(value)}</dd>
            </div>
          ))}
        </dl>
      )}
    </article>
  );
}
