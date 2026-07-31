import { useState } from "react";

import { clock } from "@/components/MatchTimeline";
import type { ItemRef, ScoreboardPlayer } from "@/types";

interface Props {
  players: ScoreboardPlayer[];
  /** Highlighted row — the account the app is currently looking at. */
  highlightAccountId: number | null;
  radiantWin: boolean | null;
}

export function Scoreboard({ players, highlightAccountId, radiantWin }: Props) {
  const radiant = players.filter((p) => p.is_radiant);
  const dire = players.filter((p) => !p.is_radiant);
  return (
    <div className="space-y-5">
      <Team
        label="Radiant"
        players={radiant}
        won={radiantWin === true}
        highlightAccountId={highlightAccountId}
      />
      <Team
        label="Dire"
        players={dire}
        won={radiantWin === false}
        highlightAccountId={highlightAccountId}
      />
    </div>
  );
}

function Team({
  label,
  players,
  won,
  highlightAccountId,
}: {
  label: string;
  players: ScoreboardPlayer[];
  won: boolean;
  highlightAccountId: number | null;
}) {
  return (
    <section>
      <h3 className="mb-2 flex items-baseline gap-2 text-sm font-medium">
        <span className={label === "Radiant" ? "text-sky-400" : "text-loss"}>{label}</span>
        <span className={`text-xs ${won ? "text-win" : "text-slate-500"}`}>
          {won ? "victory" : "defeat"}
        </span>
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[680px] border-collapse text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-slate-500">
              <th className="pb-1 text-left font-medium">Hero</th>
              <th className="pb-1 text-right font-medium">Lvl</th>
              <th className="pb-1 text-right font-medium">K/D/A</th>
              <th className="pb-1 text-right font-medium">LH/DN</th>
              <th className="pb-1 text-right font-medium">GPM</th>
              <th className="pb-1 text-right font-medium">Net</th>
              <th className="pb-1 text-right font-medium">Dmg</th>
              <th className="pb-1 pl-3 text-left font-medium">Items</th>
            </tr>
          </thead>
          <tbody>
            {players.map((p) => (
              <PlayerRow
                key={p.player_slot}
                player={p}
                highlighted={
                  highlightAccountId !== null && p.account_id === highlightAccountId
                }
              />
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PlayerRow({ player: p, highlighted }: { player: ScoreboardPlayer; highlighted: boolean }) {
  const [open, setOpen] = useState(false);
  // Only parsed matches carry timings and lane stats — nothing to expand otherwise.
  const expandable = p.purchases.length > 0 || p.lane_efficiency_pct !== null;

  return (
    <>
      <tr className={`border-t border-border-subtle ${highlighted ? "bg-surface-raised" : ""}`}>
        <td className="py-1.5">
          <span className="flex items-center gap-2">
            {p.hero_icon_url && (
              <img src={p.hero_icon_url} alt="" loading="lazy" className="size-5" />
            )}
            {expandable ? (
              <button
                type="button"
                onClick={() => setOpen((v) => !v)}
                className="truncate text-slate-200 underline decoration-dotted underline-offset-2 hover:text-white"
                title="Show item timings and lane stats"
              >
                {p.hero_name ?? `hero ${p.hero_id}`}
              </button>
            ) : (
              <span className="truncate text-slate-200">
                {p.hero_name ?? `hero ${p.hero_id}`}
              </span>
            )}
          </span>
        </td>
                <td className="text-right font-mono text-xs text-slate-400">{p.level}</td>
                <td className="text-right font-mono text-xs text-slate-300">
                  {p.kills}/{p.deaths}/{p.assists}
                </td>
                <td className="text-right font-mono text-xs text-slate-400">
                  {p.last_hits}/{p.denies}
                </td>
                <td className="text-right font-mono text-xs text-slate-400">
                  {p.gold_per_min}
                </td>
                <td className="text-right font-mono text-xs text-warn">
                  {p.net_worth ? `${(p.net_worth / 1000).toFixed(1)}k` : "—"}
                </td>
                <td className="text-right font-mono text-xs text-slate-400">
                  {p.hero_damage ? `${(p.hero_damage / 1000).toFixed(1)}k` : "—"}
                </td>
        <td className="py-1.5 pl-3">
          <Inventory player={p} />
        </td>
      </tr>

      {open && (
        <tr className="border-t border-border-subtle/50 bg-surface-raised/40">
          <td colSpan={8} className="px-2 py-3">
            <ParsedDetail player={p} />
          </td>
        </tr>
      )}
    </>
  );
}

function ParsedDetail({ player: p }: { player: ScoreboardPlayer }) {
  return (
    <div className="space-y-3">
      <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs">
        <Stat label="lane efficiency" value={pct(p.lane_efficiency_pct)} />
        <Stat
          label="teamfight participation"
          value={
            p.teamfight_participation === null
              ? null
              : `${Math.round(p.teamfight_participation * 100)}%`
          }
        />
        <Stat label="APM" value={p.actions_per_min} />
        <Stat label="neutral kills" value={p.neutral_kills} />
        <Stat label="towers" value={p.tower_kills} />
        <Stat label="buybacks" value={p.buyback_count} />
        <Stat label="wards" value={`${p.obs_placed ?? 0} obs / ${p.sen_placed ?? 0} sen`} />
      </dl>

      {p.purchases.length > 0 && (
        <div>
          <p className="mb-1 text-xs uppercase tracking-wider text-slate-500">
            Item timings
          </p>
          <ol className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs">
            {p.purchases.map((purchase, index) => (
              <li key={`${purchase.name}-${index}`} className="flex items-center gap-1.5">
                {purchase.image_url && (
                  <img
                    src={purchase.image_url}
                    alt=""
                    loading="lazy"
                    className="h-4 w-[22px] rounded-sm object-cover"
                  />
                )}
                <span className="text-slate-300">{purchase.name}</span>
                <span className="font-mono text-slate-500">{clock(purchase.time)}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number | null }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex gap-1.5">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-mono text-slate-300">{value}</dd>
    </div>
  );
}

function pct(value: number | null): string | null {
  return value === null ? null : `${value}%`;
}

function Inventory({ player }: { player: ScoreboardPlayer }) {
  return (
    <span className="flex items-center gap-0.5">
      {player.items.map((item, index) => (
        <ItemIcon key={`${item.id}-${index}`} item={item} />
      ))}
      {player.backpack.length > 0 && (
        <span className="mx-1 h-5 w-px bg-border-subtle" title="Backpack" />
      )}
      {player.backpack.map((item, index) => (
        <ItemIcon key={`bp-${item.id}-${index}`} item={item} dim />
      ))}
      {player.neutral_item && (
        <>
          <span className="mx-1 h-5 w-px bg-border-subtle" title="Neutral item" />
          <ItemIcon item={player.neutral_item} round />
        </>
      )}
    </span>
  );
}

function ItemIcon({
  item,
  dim = false,
  round = false,
}: {
  item: ItemRef;
  dim?: boolean;
  round?: boolean;
}) {
  if (!item.image_url) {
    return (
      <span className="rounded bg-surface px-1 text-[10px] text-slate-500" title={item.name}>
        {item.name.slice(0, 2)}
      </span>
    );
  }
  return (
    <img
      src={item.image_url}
      alt={item.name}
      title={item.name}
      loading="lazy"
      className={`h-5 w-[27px] object-cover ${round ? "rounded-full" : "rounded-sm"} ${
        dim ? "opacity-50" : ""
      }`}
    />
  );
}
