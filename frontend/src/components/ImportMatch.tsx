import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "@/api";
import type { MatchImportResult, MatchSlot } from "@/types";

interface Props {
  accountId: number | null;
  viewingSelf: boolean;
  onImported: () => void;
}

/**
 * Analyse one match by id. This is the way in for accounts whose match history
 * isn't public — the match is public even when the player in it is anonymous.
 */
export function ImportMatch({ accountId, viewingSelf, onImported }: Props) {
  const [matchInput, setMatchInput] = useState("");
  const [result, setResult] = useState<MatchImportResult | null>(null);

  const load = useMutation({
    mutationFn: ({ matchId, slot }: { matchId: number; slot?: number }) =>
      api.importMatch(matchId, viewingSelf ? null : accountId, slot),
    onSuccess: (data) => {
      setResult(data);
      if (data.resolved) {
        setMatchInput("");
        onImported();
      }
    },
  });

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const matchId = Number.parseInt(matchInput, 10);
    if (Number.isFinite(matchId)) {
      setResult(null);
      load.mutate({ matchId });
    }
  };

  return (
    <div className="mb-8">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Add a match by id
      </h2>
      <form className="flex gap-2" onSubmit={submit}>
        <input
          value={matchInput}
          onChange={(event) => setMatchInput(event.target.value)}
          placeholder="e.g. 8922669985"
          inputMode="numeric"
          className="w-48 rounded-md border border-border-subtle bg-surface-raised px-3 py-1.5 text-sm placeholder:text-slate-500 focus:border-slate-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={load.isPending || accountId === null}
          className="rounded-md border border-border-subtle px-3 py-1.5 text-sm hover:bg-surface-raised disabled:opacity-40"
        >
          {load.isPending ? "Loading…" : "Analyse"}
        </button>
      </form>

      {load.isError && (
        <p className="mt-2 text-sm text-loss">{String(load.error)}</p>
      )}

      {result && !result.resolved && (
        <SlotPicker
          candidates={result.candidates}
          disabled={load.isPending}
          onPick={(slot) =>
            load.mutate({ matchId: result.match_id, slot })
          }
        />
      )}

      {result?.resolved && (
        <p className="mt-2 text-sm text-slate-400">
          Added — {result.insights_created}{" "}
          {result.insights_created === 1 ? "finding" : "findings"}
          {result.is_parsed ? "" : " (replay not parsed, so only summary rules ran)"}
        </p>
      )}
    </div>
  );
}

function SlotPicker({
  candidates,
  disabled,
  onPick,
}: {
  candidates: MatchSlot[];
  disabled: boolean;
  onPick: (slot: number) => void;
}) {
  return (
    <div className="mt-3 rounded-md border border-warn/50 bg-warn/5 p-3">
      <p className="mb-2 text-sm text-slate-300">
        You&apos;re anonymous in this match, so pick which player was you.
      </p>
      <div className="grid gap-1 sm:grid-cols-2">
        {candidates.map((slot) => (
          <button
            key={slot.player_slot}
            type="button"
            disabled={disabled}
            onClick={() => onPick(slot.player_slot)}
            className="flex items-center gap-2 rounded border border-border-subtle px-2 py-1.5 text-left text-xs hover:bg-surface-raised disabled:opacity-40"
          >
            <span className={slot.is_radiant ? "text-win" : "text-loss"}>
              {slot.is_radiant ? "R" : "D"}
            </span>
            <span className="w-16 text-slate-300">hero {slot.hero_id}</span>
            <span className="font-mono text-slate-400">
              {slot.kills}/{slot.deaths}/{slot.assists}
            </span>
            <span className="ml-auto font-mono text-slate-500">
              {slot.gold_per_min} gpm
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
