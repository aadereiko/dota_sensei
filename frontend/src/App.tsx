import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { api, UnauthorizedError } from "@/api";
import { ImportMatch } from "@/components/ImportMatch";
import { InsightCard } from "@/components/InsightCard";
import { MatchRow } from "@/components/MatchRow";
import { SignedInAs, SteamLoginButton } from "@/components/SteamAuth";

export default function App() {
  const queryClient = useQueryClient();
  const [accountInput, setAccountInput] = useState("");
  const [accountId, setAccountId] = useState<number | null>(null);
  const [selectedMatchId, setSelectedMatchId] = useState<number | null>(null);

  // Steam bounces back to /?login=ok|failed after the OpenID round trip.
  const loginStatus = new URLSearchParams(window.location.search).get("login");
  useEffect(() => {
    if (loginStatus) {
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [loginStatus]);

  const me = useQuery({
    queryKey: ["me"],
    queryFn: api.me,
    // A 401 just means signed out — don't retry it.
    retry: (count, error) => !(error instanceof UnauthorizedError) && count < 1,
  });
  const signedIn = me.data ?? null;

  // Signed in? That's the account we look at, unless one was typed in manually.
  const { data: config } = useQuery({ queryKey: ["config"], queryFn: api.config });
  useEffect(() => {
    if (accountId !== null) return;
    const preset = signedIn?.account_id ?? config?.default_account_id ?? null;
    if (preset !== null) {
      setAccountId(preset);
      setAccountInput(String(preset));
    }
  }, [signedIn, config, accountId]);

  const viewingSelf = signedIn !== null && signedIn.account_id === accountId;

  const matches = useQuery({
    queryKey: ["matches", accountId],
    queryFn: () => api.matches(accountId!),
    enabled: accountId !== null,
  });

  const recurring = useQuery({
    queryKey: ["recurring", accountId],
    queryFn: () => api.recurring(accountId!),
    enabled: accountId !== null,
  });

  const detail = useQuery({
    queryKey: ["match", accountId, selectedMatchId],
    queryFn: () => api.match(accountId!, selectedMatchId!),
    enabled: accountId !== null && selectedMatchId !== null,
  });

  const sync = useMutation({
    // Signed in and looking at yourself? Let the server use the session.
    mutationFn: () => api.sync(viewingSelf ? null : accountId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["matches", accountId] });
      queryClient.invalidateQueries({ queryKey: ["recurring", accountId] });
    },
  });

  const signOut = useMutation({
    mutationFn: api.logout,
    onSuccess: () => {
      setAccountId(null);
      setAccountInput("");
      setSelectedMatchId(null);
      queryClient.clear();
    },
  });

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-border-subtle pb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">dota_sensei</h1>
          <p className="mt-1 text-sm text-slate-400">
            Your last games, and what went wrong in them.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {me.isLoading ? null : signedIn ? (
            <SignedInAs user={signedIn} onSignOut={() => signOut.mutate()} />
          ) : (
            <SteamLoginButton />
          )}
          <button
            type="button"
            disabled={accountId === null || sync.isPending}
            onClick={() => sync.mutate()}
            className="rounded-md border border-border-subtle px-3 py-1.5 text-sm hover:bg-surface-raised disabled:opacity-40"
          >
            {sync.isPending ? "Syncing…" : "Sync"}
          </button>
        </div>
      </header>

      {loginStatus === "failed" && (
        <p className="mt-4 text-sm text-loss">
          Steam sign-in didn&apos;t complete. Try again.
        </p>
      )}
      {sync.isError && (
        <p className="mt-4 text-sm text-loss">Sync failed: {String(sync.error)}</p>
      )}

      {accountId === null ? (
        <div className="mt-10 space-y-4">
          <p className="text-sm text-slate-400">
            Sign in through Steam to analyse your own matches.
          </p>
          <SteamLoginButton />
          <form
            className="flex gap-2 pt-4"
            onSubmit={(event) => {
              event.preventDefault();
              const parsed = Number.parseInt(accountInput, 10);
              if (Number.isFinite(parsed)) {
                setAccountId(parsed);
                setSelectedMatchId(null);
              }
            }}
          >
            <input
              value={accountInput}
              onChange={(event) => setAccountInput(event.target.value)}
              placeholder="…or paste any account id"
              inputMode="numeric"
              className="w-56 rounded-md border border-border-subtle bg-surface-raised px-3 py-1.5 text-sm placeholder:text-slate-500 focus:border-slate-400 focus:outline-none"
            />
            <button
              type="submit"
              className="rounded-md border border-border-subtle px-3 py-1.5 text-sm hover:bg-surface-raised"
            >
              Load
            </button>
          </form>
        </div>
      ) : (
        <div className="mt-8 grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
          <section>
            {!viewingSelf && (
              <p className="mb-4 text-xs text-slate-500">
                Viewing account <span className="font-mono">{accountId}</span>
              </p>
            )}

            <ImportMatch
              accountId={accountId}
              viewingSelf={viewingSelf}
              onImported={() => {
                queryClient.invalidateQueries({ queryKey: ["matches", accountId] });
                queryClient.invalidateQueries({ queryKey: ["recurring", accountId] });
              }}
            />

            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Recurring mistakes
            </h2>
            {recurring.data?.length ? (
              <ul className="mb-8 space-y-1.5">
                {recurring.data.map((item) => (
                  <li
                    key={item.rule_key}
                    className="flex items-baseline justify-between gap-3 rounded-md border border-border-subtle px-3 py-2 text-sm"
                  >
                    <span className="text-slate-200">{item.title}</span>
                    <span className="shrink-0 font-mono text-xs text-slate-400">
                      ×{item.occurrences}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mb-8 text-sm text-slate-500">Nothing yet — hit Sync.</p>
            )}

            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Recent matches
            </h2>
            {matches.isLoading && <p className="text-sm text-slate-500">Loading…</p>}
            <div className="space-y-0.5">
              {matches.data?.map((match) => (
                <MatchRow
                  key={match.match_id}
                  match={match}
                  selected={match.match_id === selectedMatchId}
                  onSelect={setSelectedMatchId}
                />
              ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Breakdown
            </h2>
            {selectedMatchId === null ? (
              <p className="text-sm text-slate-500">Pick a match on the left.</p>
            ) : detail.isLoading ? (
              <p className="text-sm text-slate-500">Loading…</p>
            ) : detail.data?.insights.length ? (
              <div className="space-y-3">
                {detail.data.insights.map((insight) => (
                  <InsightCard key={insight.rule_key} insight={insight} />
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-500">
                {detail.data?.is_parsed === false
                  ? "This replay isn't parsed by OpenDota, so only the summary-level " +
                    "rules could run. Request a parse to get lane and timeline analysis."
                  : "No mistakes flagged in this one. Clean game."}
              </p>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
