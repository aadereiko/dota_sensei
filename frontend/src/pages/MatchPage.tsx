import { useQuery } from "@tanstack/react-query";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { api } from "@/api";
import { AdvantageChart } from "@/components/AdvantageChart";
import { InsightCard } from "@/components/InsightCard";
import { PageHeader } from "@/components/Layout";
import { MatchTimeline } from "@/components/MatchTimeline";
import { RequestParse } from "@/components/RequestParse";
import { Scoreboard } from "@/components/Scoreboard";

function gold(value: number): string {
  return value >= 1000 ? `${(value / 1000).toFixed(1)}k` : String(value);
}

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
          <div className="space-y-3 rounded-lg border border-border-subtle bg-surface-raised p-4">
            <p className="text-sm text-slate-400">
              OpenDota hasn&apos;t parsed this replay, so there are no per-minute
              graphs, item timings, lane stats or objective log. The scoreboard above
              comes from summary data, which is always available.
            </p>
            <p className="text-sm text-slate-500">
              You can ask for a parse — it&apos;s free, and it also lets the analysis
              rules that need lane roles run on this game.
            </p>
            <RequestParse matchId={m.match_id} />
          </div>
        )}
      </section>

      {m.events.length > 0 && (
        <section className="mt-8">
          <h2 className="mb-3 flex items-baseline gap-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
            Key moments
            <span className="font-normal normal-case tracking-normal text-slate-500">
              {/* stomp/comeback are gold amounts, not flags — rendering them as
                  badges would call every game a stomp. */}
              {m.teamfight_count !== null && `${m.teamfight_count} teamfights`}
              {m.stomp ? ` · winner led by up to ${gold(m.stomp)}` : ""}
              {m.comeback ? ` · came back from ${gold(m.comeback)} down` : ""}
            </span>
          </h2>
          <MatchTimeline events={m.events} />
        </section>
      )}

      <div className="mt-8">
        <Link to="/" className="text-sm text-slate-400 underline hover:text-slate-200">
          ← Back to matches
        </Link>
      </div>
    </>
  );
}
