"use client";

// Page buttons to show: the first and last pages and the ones around the current page. Bigger gaps become "…".
function pageButtons(page: number, pageCount: number): (number | "gap")[] {
  const pages = [...new Set([1, page - 1, page, page + 1, pageCount])]
    .filter((p) => p >= 1 && p <= pageCount)
    .sort((a, b) => a - b);
  const buttons: (number | "gap")[] = [];
  pages.forEach((p, i) => {
    const step = i > 0 ? p - pages[i - 1] : 1;
    if (step === 2) buttons.push(p - 1); // only one page missing: show it instead of "…"
    if (step > 2) buttons.push("gap");
    buttons.push(p);
  });
  return buttons;
}

export default function Pagination({
  page,
  pageSize,
  total,
  pageSizeOptions,
  disabled = false,
  onPageChange,
  onPageSizeChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  pageSizeOptions?: number[];
  disabled?: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
}) {
  if (total === 0) return null;
  const pageCount = Math.ceil(total / pageSize);
  const first = (page - 1) * pageSize + 1;
  const last = Math.min(page * pageSize, total);

  return (
    <nav aria-label="Pages" className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-[13px] text-[var(--muted)]">
        {pageSizeOptions && onPageSizeChange && (
          <label className="flex items-center gap-2">
            Rows per page
            <select
              value={pageSize}
              onChange={(e) => onPageSizeChange(Number(e.target.value))}
              disabled={disabled}
              className="input-field input-sm"
            >
              {pageSizeOptions.map((size) => (
                <option key={size} value={size}>
                  {size}
                </option>
              ))}
            </select>
          </label>
        )}
        <span>
          {first.toLocaleString()}–{last.toLocaleString()} of {total.toLocaleString()}
        </span>
      </div>

      <div className="flex items-center gap-1.5">
        <button
          type="button"
          onClick={() => onPageChange(page - 1)}
          disabled={disabled || page <= 1}
          className="chip disabled:pointer-events-none disabled:opacity-35"
        >
          ‹ Prev
        </button>

        <div className="hidden items-center gap-1.5 sm:flex">
          {pageButtons(page, pageCount).map((p, i) =>
            p === "gap" ? (
              <span key={`gap-${i}`} className="px-1 text-[13px] text-[var(--muted)]">
                …
              </span>
            ) : (
              <button
                key={p}
                type="button"
                onClick={() => p !== page && onPageChange(p)}
                disabled={disabled && p !== page}
                aria-current={p === page ? "page" : undefined}
                className={`chip min-w-10 disabled:pointer-events-none disabled:opacity-35 ${
                  p === page ? "chip-selected" : ""
                }`}
              >
                {p}
              </button>
            )
          )}
        </div>
        <span className="px-2 text-[13px] text-[var(--muted)] sm:hidden">
          {page} / {pageCount}
        </span>

        <button
          type="button"
          onClick={() => onPageChange(page + 1)}
          disabled={disabled || page >= pageCount}
          className="chip disabled:pointer-events-none disabled:opacity-35"
        >
          Next ›
        </button>
      </div>
    </nav>
  );
}
