import type { MatchSummary } from "@/types";

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  return `${mins}:${String(seconds % 60).padStart(2, "0")}`;
}

interface Props {
  match: MatchSummary;
  selected: boolean;
  onSelect: (matchId: number) => void;
}

export function MatchRow({ match, selected, onSelect }: Props) {
  return (
    <button
      type="button"
      onClick={() => onSelect(match.match_id)}
      className={`flex w-full items-center gap-4 rounded-md border px-3 py-2 text-left text-sm transition
        ${
          selected
            ? "border-slate-400 bg-surface-raised"
            : "border-transparent hover:border-border-subtle hover:bg-surface-raised/60"
        }`}
    >
      <span
        className={`w-6 font-semibold ${match.won ? "text-win" : "text-loss"}`}
        title={match.won ? "win" : "loss"}
      >
        {match.won ? "W" : "L"}
      </span>
      {/* Hero names need the /heroStats lookup — showing the id until that lands. */}
      <span className="w-20 text-slate-300">hero {match.hero_id}</span>
      <span className="w-20 font-mono text-slate-400">
        {match.kills}/{match.deaths}/{match.assists}
      </span>
      <span className="w-16 font-mono text-slate-500">
        {formatDuration(match.duration_seconds)}
      </span>
      <span className="w-20 font-mono text-slate-500">{match.gold_per_min} gpm</span>
      {match.insight_count > 0 && (
        <span
          className={`ml-auto rounded-full px-2 py-0.5 text-xs
            ${match.worst_severity === "critical" ? "bg-loss/20 text-loss" : "bg-warn/20 text-warn"}`}
        >
          {match.insight_count} {match.insight_count === 1 ? "note" : "notes"}
        </span>
      )}
    </button>
  );
}
