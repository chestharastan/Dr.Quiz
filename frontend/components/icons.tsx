// Line icons in the spirit of SF Symbols. Size them with CSS (e.g. `.nav-item svg`) or a className.

type IconProps = { className?: string };

const stroke = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function QuestionsIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <rect x="4" y="3.5" width="16" height="17" rx="3" />
      <path d="M8 8.5h8M8 12h8M8 15.5h5" />
    </svg>
  );
}

export function UsersIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <circle cx="9" cy="8.5" r="3.2" />
      <path d="M3.5 19c.6-3.2 2.8-5 5.5-5s4.9 1.8 5.5 5" />
      <circle cx="17" cy="9.5" r="2.4" />
      <path d="M16.5 14.2c2.2.2 3.6 1.7 4 4.3" />
    </svg>
  );
}

export function TasksIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <path d="M4 6.5l1.6 1.6L8.5 5M4 12.5l1.6 1.6 2.9-3.1M4 18.5l1.6 1.6 2.9-3.1" />
      <path d="M11.5 7h8.5M11.5 13h8.5M11.5 19h8.5" />
    </svg>
  );
}

export function PlayIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M10.2 8.9v6.2l5-3.1z" fill="currentColor" />
    </svg>
  );
}

export function LogoutIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <path d="M10 4.5H6.5A2.5 2.5 0 0 0 4 7v10a2.5 2.5 0 0 0 2.5 2.5H10" />
      <path d="M15 8l4 4-4 4M19 12H9.5" />
    </svg>
  );
}

export function SearchIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="M20 20l-4.2-4.2" />
    </svg>
  );
}

export function DownloadIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <path d="M12 4v11M7.5 10.5L12 15l4.5-4.5M5 19.5h14" />
    </svg>
  );
}

export function ChevronRightIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

export function GridIcon({ className }: IconProps) {
  return (
    <svg {...stroke} className={className}>
      <rect x="4" y="4" width="7" height="7" rx="2" />
      <rect x="13" y="4" width="7" height="7" rx="2" />
      <rect x="4" y="13" width="7" height="7" rx="2" />
      <rect x="13" y="13" width="7" height="7" rx="2" />
    </svg>
  );
}
