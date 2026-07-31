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
              <tr
                key={p.player_slot}
                className={`border-t border-border-subtle ${
                  highlightAccountId !== null && p.account_id === highlightAccountId
                    ? "bg-surface-raised"
                    : ""
                }`}
              >
                <td className="py-1.5">
                  <span className="flex items-center gap-2">
                    {p.hero_icon_url && (
                      <img src={p.hero_icon_url} alt="" loading="lazy" className="size-5" />
                    )}
                    <span className="truncate text-slate-200">
                      {p.hero_name ?? `hero ${p.hero_id}`}
                    </span>
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
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
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
