import type { MatchEvent } from "@/types";

const KIND_MARK: Record<MatchEvent["kind"], string> = {
  first_blood: "◆",
  building: "▮",
  throne: "★",
  roshan: "☠",
  aegis: "✚",
};

export function MatchTimeline({ events }: { events: MatchEvent[] }) {
  if (events.length === 0) return null;
  return (
    <ol className="space-y-0.5">
      {events.map((event, index) => (
        <li
          key={`${event.time}-${index}`}
          className="flex items-baseline gap-3 rounded px-2 py-1 text-sm odd:bg-surface-raised/40"
        >
          <span className="w-12 shrink-0 text-right font-mono text-xs text-slate-500">
            {clock(event.time)}
          </span>
          <span
            className={`w-3 shrink-0 text-center text-xs ${
              event.team === "radiant"
                ? "text-sky-400"
                : event.team === "dire"
                  ? "text-loss"
                  : "text-slate-500"
            }`}
            aria-hidden
          >
            {KIND_MARK[event.kind]}
          </span>
          <span
            className={
              event.kind === "throne" ? "font-medium text-slate-100" : "text-slate-300"
            }
          >
            {event.label}
          </span>
        </li>
      ))}
    </ol>
  );
}

/** Objective times are seconds from horn; pre-horn events are negative. */
export function clock(seconds: number): string {
  const sign = seconds < 0 ? "-" : "";
  const abs = Math.abs(seconds);
  return `${sign}${Math.floor(abs / 60)}:${String(abs % 60).padStart(2, "0")}`;
}
