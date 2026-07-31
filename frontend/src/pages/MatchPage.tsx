import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api";
import { AdvantageChart } from "@/components/AdvantageChart";
import { InsightCard } from "@/components/InsightCard";
import { PageHeader } from "@/components/Layout";
import { Scoreboard } from "@/components/Scoreboard";

export default function MatchPage() {
  const { matchId } = useParams();
  const [params] = useSearchParams();
  const id = Number(matchId);
  const accountId = Number(params.get("account")) || null;

  const match = useQuery({
    queryKey: ["fullMatch", id],
    queryFn: () => api.fullMatch(id),
    enabled: Number.isFinite(id),
  });

  // The findings for whoever we're viewing as, if the caller told us.
  const mine = useQuery({
    queryKey: ["match", accountId, id],
    queryFn: () => api.match(accountId!, id),
    enabled: accountId !== null && Number.isFinite(id),
  });

  if (match.isLoading) return <p className="text-sm text-slate-500">Loading match…</p>;
  if (match.isError) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-loss">{String(match.error)}</p>
        <Link to="/" className="text-sm text-slate-400 underline">
          Back to matches
        </Link>
      </div>
    );
  }
  if (!match.data) return null;

  const m = match.data;
  const minutes = Math.floor(m.duration_seconds / 60);
  const seconds = String(m.duration_seconds % 60).padStart(2, "0");

  return (
    <>
      <PageHeader
        title={`Match ${m.match_id}`}
        subtitle={`${new Date(m.start_time).toLocaleString()} · ${minutes}:${seconds} · ${
          m.radiant_win ? "Radiant" : "Dire"
        } victory`}
      >
        <span className="font-mono text-lg">
          <span className="text-sky-400">{m.radiant_score}</span>
          <span className="mx-1.5 text-slate-600">–</span>
          <span className="text-loss">{m.dire_score}</span>
        </span>
      </PageHeader>

      {mine.data && mine.data.insights.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Your mistakes in this game
          </h2>
          <div className="space-y-3">
            {mine.data.insights.map((insight) => (
              <InsightCard key={insight.rule_key} insight={insight} />
            ))}
          </div>
        </section>
      )}

      <section className="mb-8">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          Scoreboard
        </h2>
        <Scoreboard
          players={m.players}
          highlightAccountId={accountId}
          radiantWin={m.radiant_win}
        />
      </section>

      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
          How the game went
        </h2>
        {m.is_parsed && m.radiant_gold_adv.length > 0 ? (
          // Two charts, not one with two y-axes: gold and XP are different
          // scales, and overlaying them would invent a correlation.
          <div className="grid gap-4 lg:grid-cols-2">
            <AdvantageChart title="Net gold advantage" series={m.radiant_gold_adv} />
            <AdvantageChart title="Net experience advantage" series={m.radiant_xp_adv} />
          </div>
        ) : (
          <p className="rounded-lg border border-border-subtle bg-surface-raised p-4 text-sm text-slate-500">
            OpenDota hasn&apos;t parsed this replay, so there are no per-minute graphs.
            The scoreboard above comes from the summary data, which is always available.
          </p>
        )}
      </section>

      <div className="mt-8">
        <Link to="/" className="text-sm text-slate-400 underline hover:text-slate-200">
          ← Back to matches
        </Link>
      </div>
    </>
  );
}
