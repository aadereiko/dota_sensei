import { STEAM_LOGIN_URL } from "@/api";
import type { CurrentUser } from "@/types";

export function SteamLoginButton({ label = "Sign in through Steam" }: { label?: string }) {
  return (
    <a
      href={STEAM_LOGIN_URL}
      className="inline-flex items-center gap-2 rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-900 hover:bg-white"
    >
      <SteamMark />
      {label}
    </a>
  );
}

export function SignedInAs({ user, onSignOut }: { user: CurrentUser; onSignOut: () => void }) {
  return (
    <div className="flex items-center gap-3">
      {user.avatar_url && (
        <img
          src={user.avatar_url}
          alt=""
          className="size-8 rounded-full border border-border-subtle"
        />
      )}
      <div className="leading-tight">
        <div className="text-sm text-slate-200">{user.persona_name ?? "Signed in"}</div>
        <div className="font-mono text-xs text-slate-500">{user.account_id}</div>
      </div>
      <button
        type="button"
        onClick={onSignOut}
        className="rounded-md border border-border-subtle px-2 py-1 text-xs text-slate-400 hover:bg-surface-raised"
      >
        Sign out
      </button>
    </div>
  );
}

function SteamMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden className="size-4 fill-current">
      <path d="M12 0C5.6 0 .4 4.9 0 11.1l6.4 2.7c.5-.4 1.2-.6 1.9-.6h.2l2.9-4.1v-.1c0-2.5 2-4.5 4.5-4.5s4.5 2 4.5 4.5-2 4.5-4.6 4.5h-.1l-4.1 2.9v.2c0 1.9-1.5 3.4-3.4 3.4-1.6 0-3-1.2-3.3-2.7L.1 15.4C1.5 20.3 6.3 24 12 24c6.6 0 12-5.4 12-12S18.6 0 12 0zM7.5 18.2l-1.5-.6c.3.6.8 1 1.5 1.3 1.4.6 3-.1 3.5-1.5.3-.7.3-1.4 0-2.1s-.9-1.2-1.5-1.5c-.7-.3-1.4-.3-2 0l1.5.6c1 .4 1.5 1.6 1.1 2.6s-1.6 1.6-2.6 1.2zm11-8.9c0-1.7-1.3-3-3-3s-3 1.4-3 3 1.4 3 3 3 3-1.3 3-3zm-5.2 0c0-1.2 1-2.2 2.3-2.2s2.2 1 2.2 2.2-1 2.3-2.2 2.3-2.3-1-2.3-2.3z" />
    </svg>
  );
}
