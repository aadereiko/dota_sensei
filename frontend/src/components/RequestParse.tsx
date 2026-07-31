import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api } from "@/api";

/**
 * Ask OpenDota to parse this replay.
 *
 * Parsing is free but queued, and it's what unlocks lane roles, per-minute
 * series, the objective log and item timings — so the rules that can't run on an
 * unparsed match start working afterwards. The backend re-ingests and re-runs
 * the analysis once the job lands.
 */
export function RequestParse({ matchId }: { matchId: number }) {
  const queryClient = useQueryClient();
  const [jobId, setJobId] = useState<number | null>(null);

  const start = useMutation({
    mutationFn: () => api.requestParse(matchId),
    onSuccess: (status) => {
      if (status.is_parsed) {
        queryClient.invalidateQueries({ queryKey: ["fullMatch", matchId] });
      } else {
        setJobId(status.job_id);
      }
    },
  });

  // Poll while queued. Parses usually land in a minute or two, but can take
  // longer when OpenDota is busy — hence a slow interval rather than a spinner
  // that implies it's about to finish.
  const poll = useQuery({
    queryKey: ["parse", matchId, jobId],
    queryFn: () => api.checkParse(matchId, jobId!),
    enabled: jobId !== null,
    refetchInterval: (query) => (query.state.data?.is_parsed ? false : 15_000),
  });

  const parsed = poll.data?.is_parsed ?? false;
  useEffect(() => {
    // Refetching the match is a side effect, so it belongs here rather than in
    // the render path.
    if (parsed) queryClient.invalidateQueries({ queryKey: ["fullMatch", matchId] });
  }, [parsed, matchId, queryClient]);

  const waiting = jobId !== null && !parsed;

  return (
    <div className="space-y-2">
      <button
        type="button"
        disabled={start.isPending || waiting}
        onClick={() => start.mutate()}
        className="rounded-md border border-border-subtle px-3 py-1.5 text-sm hover:bg-surface-raised disabled:opacity-40"
      >
        {start.isPending ? "Requesting…" : waiting ? "Parsing…" : "Request parse"}
      </button>
      {waiting && (
        <p className="text-xs text-slate-500">
          Queued with OpenDota (job {jobId}). This can take a few minutes; the page
          updates itself when it lands. Leaving and coming back is fine — re-request
          to pick the poll back up.
        </p>
      )}
      {start.isError && <p className="text-xs text-loss">{String(start.error)}</p>}
    </div>
  );
}
