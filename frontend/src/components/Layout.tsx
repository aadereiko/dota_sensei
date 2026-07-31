import { NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/", label: "Matches", end: true },
  { to: "/heroes", label: "Heroes", end: false },
  { to: "/items", label: "Items", end: false },
];

export function Layout() {
  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <nav className="mb-8 flex gap-1 border-b border-border-subtle pb-3">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `rounded-md px-3 py-1.5 text-sm transition ${
                isActive
                  ? "bg-surface-raised text-slate-100"
                  : "text-slate-400 hover:text-slate-200"
              }`
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}

/** Shared header for the reference pages. */
export function PageHeader({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
      </div>
      {children}
    </header>
  );
}

export function SearchInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <input
      value={value}
      onChange={(event) => onChange(event.target.value)}
      placeholder={placeholder}
      className="w-52 rounded-md border border-border-subtle bg-surface-raised px-3 py-1.5 text-sm placeholder:text-slate-500 focus:border-slate-400 focus:outline-none"
    />
  );
}

/** Pill row for filtering by a single value; null means "all". */
export function FilterPills<T extends string | number>({
  options,
  active,
  onChange,
  labels,
}: {
  options: T[];
  active: T | null;
  onChange: (value: T | null) => void;
  labels?: Record<string, string>;
}) {
  return (
    <div className="mb-5 flex flex-wrap gap-1.5">
      <Pill selected={active === null} onClick={() => onChange(null)}>
        All
      </Pill>
      {options.map((option) => (
        <Pill
          key={String(option)}
          selected={active === option}
          onClick={() => onChange(active === option ? null : option)}
        >
          {labels?.[String(option)] ?? String(option)}
        </Pill>
      ))}
    </div>
  );
}

function Pill({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full border px-2.5 py-1 text-xs capitalize transition ${
        selected
          ? "border-slate-400 bg-surface-raised text-slate-100"
          : "border-border-subtle text-slate-400 hover:text-slate-200"
      }`}
    >
      {children}
    </button>
  );
}
