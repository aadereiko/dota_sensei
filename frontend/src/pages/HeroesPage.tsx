import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { api } from "@/api";
import { FilterPills, PageHeader, SearchInput } from "@/components/Layout";
import type { Hero } from "@/types";

const ATTR_LABELS: Record<string, string> = {
  str: "Strength",
  agi: "Agility",
  int: "Intelligence",
  all: "Universal",
};

const ATTR_COLORS: Record<string, string> = {
  str: "text-loss",
  agi: "text-win",
  int: "text-sky-400",
  all: "text-warn",
};

export default function HeroesPage() {
  const [search, setSearch] = useState("");
  const [attr, setAttr] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  // Static within a patch — no reason to refetch it.
  const heroes = useQuery({
    queryKey: ["heroes"],
    queryFn: api.heroes,
    staleTime: Infinity,
  });

  const roles = useMemo(() => {
    const all = new Set<string>();
    heroes.data?.forEach((h) => h.roles.forEach((r) => all.add(r)));
    return [...all].sort();
  }, [heroes.data]);

  const shown = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return (heroes.data ?? []).filter((h) => {
      if (needle && !h.localized_name.toLowerCase().includes(needle)) return false;
      if (attr && h.primary_attr !== attr) return false;
      if (role && !h.roles.includes(role)) return false;
      return true;
    });
  }, [heroes.data, search, attr, role]);

  return (
    <>
      <PageHeader
        title="Heroes"
        subtitle={
          heroes.data
            ? `${shown.length} of ${heroes.data.length} heroes`
            : "Loading from OpenDota…"
        }
      >
        <SearchInput value={search} onChange={setSearch} placeholder="Search heroes" />
      </PageHeader>

      <FilterPills
        options={["str", "agi", "int", "all"]}
        active={attr}
        onChange={setAttr}
        labels={ATTR_LABELS}
      />
      <FilterPills options={roles} active={role} onChange={setRole} />

      {heroes.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
      {heroes.isError && (
        <p className="text-sm text-loss">Couldn&apos;t load heroes: {String(heroes.error)}</p>
      )}
      {heroes.data && shown.length === 0 && (
        <p className="text-sm text-slate-500">No hero matches those filters.</p>
      )}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {shown.map((hero) => (
          <HeroCard key={hero.id} hero={hero} />
        ))}
      </div>
    </>
  );
}

function HeroCard({ hero }: { hero: Hero }) {
  return (
    <article className="flex gap-3 rounded-lg border border-border-subtle bg-surface-raised p-3">
      {hero.image_url && (
        <img
          src={hero.image_url}
          alt=""
          loading="lazy"
          className="h-12 w-[74px] shrink-0 rounded object-cover"
        />
      )}
      <div className="min-w-0">
        <h2 className="truncate font-medium text-slate-100">{hero.localized_name}</h2>
        <p className="mt-0.5 text-xs text-slate-500">
          <span className={ATTR_COLORS[hero.primary_attr ?? ""] ?? "text-slate-400"}>
            {ATTR_LABELS[hero.primary_attr ?? ""] ?? "—"}
          </span>
          {hero.attack_type && ` · ${hero.attack_type}`}
        </p>
        <p className="mt-1 truncate text-xs text-slate-400" title={hero.roles.join(", ")}>
          {hero.roles.join(" · ") || "—"}
        </p>
      </div>
    </article>
  );
}
