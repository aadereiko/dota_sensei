import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "@/api";
import { FilterPills, PageHeader, SearchInput } from "@/components/Layout";
import type { Item } from "@/types";

// OpenDota's `qual` field. Null covers recipes and neutrals, which get their own
// buckets below rather than being lumped into "uncategorised".
const QUALITY_ORDER = [
  "consumable",
  "component",
  "common",
  "secret_shop",
  "rare",
  "epic",
  "artifact",
];

const QUALITY_COLORS: Record<string, string> = {
  consumable: "text-slate-400",
  component: "text-sky-400",
  common: "text-win",
  secret_shop: "text-warn",
  rare: "text-indigo-400",
  epic: "text-fuchsia-400",
  artifact: "text-loss",
};

type Bucket = "all" | "purchasable" | "recipes" | "neutrals";

export default function ItemsPage() {
  const [search, setSearch] = useState("");
  const [quality, setQuality] = useState<string | null>(null);
  const [bucket, setBucket] = useState<Bucket>("purchasable");

  const items = useQuery({
    queryKey: ["items"],
    queryFn: api.items,
    staleTime: Infinity,
  });

  const shown = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (items.data ?? []).filter((item) => {
      const isRecipe = item.name.startsWith("recipe_");
      const isNeutral = item.tier !== null;
      if (bucket === "recipes" && !isRecipe) return false;
      if (bucket === "neutrals" && !isNeutral) return false;
      if (bucket === "purchasable" && (isRecipe || isNeutral)) return false;
      if (needle && !item.localized_name.toLowerCase().includes(needle)) return false;
      if (quality && item.quality !== quality) return false;
      return true;
    });
  }, [items.data, search, quality, bucket]);

  return (
    <>
      <PageHeader
        title="Items"
        subtitle={
          items.data
            ? `${shown.length} of ${items.data.length} items`
            : "Loading from OpenDota…"
        }
      >
        <SearchInput value={search} onChange={setSearch} placeholder="Search items" />
      </PageHeader>

      <div className="mb-5 flex flex-wrap gap-1.5">
        {(["purchasable", "neutrals", "recipes", "all"] as Bucket[]).map((b) => (
          <button
            key={b}
            type="button"
            onClick={() => setBucket(b)}
            className={`rounded-full border px-2.5 py-1 text-xs capitalize transition ${
              bucket === b
                ? "border-slate-400 bg-surface-raised text-slate-100"
                : "border-border-subtle text-slate-400 hover:text-slate-200"
            }`}
          >
            {b}
          </button>
        ))}
      </div>

      <FilterPills options={QUALITY_ORDER} active={quality} onChange={setQuality} />

      {items.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {items.isError && (
        <p className="text-sm text-loss">Couldn&apos;t load items: {String(items.error)}</p>
      )}
      {items.data && shown.length === 0 && (
        <p className="text-sm text-slate-500">No item matches those filters.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {shown.map((item) => (
          <ItemCard key={item.id} item={item} />
        ))}
      </div>
    </>
  );
}

function ItemCard({ item }: { item: Item }) {
  return (
    <article className="flex gap-3 rounded-lg border border-border-subtle bg-surface-raised p-3">
      {item.image_url && (
        <img
          src={item.image_url}
          alt=""
          loading="lazy"
          className="h-8 w-[43px] shrink-0 rounded object-cover"
        />
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <h2 className="truncate font-medium text-slate-100">{item.localized_name}</h2>
          {item.cost ? (
            <span className="shrink-0 font-mono text-xs text-warn">{item.cost}</span>
          ) : null}
        </div>
        <p className="mt-0.5 text-xs">
          <span className={QUALITY_COLORS[item.quality ?? ""] ?? "text-slate-500"}>
            {item.quality?.replace("_", " ") ?? (item.tier ? `neutral tier ${item.tier}` : "—")}
          </span>
          {item.created && <span className="text-slate-500"> · built from recipe</span>}
        </p>
        {item.components && item.components.length > 0 && (
          <p className="mt-1 truncate text-xs text-slate-400">
            {item.components.map((c) => c.replaceAll("_", " ")).join(" + ")}
          </p>
        )}
        {item.notes && (
          <p className="mt-1 line-clamp-2 text-xs text-slate-500">{item.notes}</p>
        )}
      </div>
    </article>
  );
}
