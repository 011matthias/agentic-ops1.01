# Lovable prompt: Email intake becomes Receipt overview (backlog item 248)

**What this is.** Dirk, 2026-10-07: users should see and filter every receipt
in one place. The Email intake page listed MAILS (the newest 100, one row per
message), so an uploaded receipt never appeared there and a mailed one was a
line inside an expander. This renames the page to **Receipt overview** and
gives it a receipt-first table: one row per receipt from every source, with
fuzzy search across all columns, a filter on every column, status pills,
column toggles, paging, and the settings remembered per browser. The old mail
log stays, unchanged, as the page's second tab ("Emails"), so held mail,
refusals, retry and dismiss are all still where Criss knows them.

**Library.** TanStack Table v8 (`@tanstack/react-table@8.21.3`) with
`@tanstack/match-sorter-utils@8.19.4` for the ranking. Pinned to v8 on purpose:
v9 (current `latest`) changed the API (`tableFeatures`, `useTable`), and every
shadcn data-table example and every model's knowledge is v8, so later edits
from Lovable stay reliable. Search is a pre-filter so the filter counts and
the pages follow it: each word must land in some field (substring, word start
or acronym; letters-in-order only when they sit close together; one typo
allowed in words of five letters or more).

**Fits the 2026-10-07 visibility rule** (item 247, `lovable-responsive-full-visibility-prompt.md`): no text is
shortened (long subjects and file names wrap inside their column), and the
table sits in an `overflow-x-auto` box that item 247's `fit-tables` measures
against, so once 247 is pasted the table turns into labelled cards on a narrow
screen like every other table. Paste after 247 or before it, either order works.

**Backend gate.** Needs `GET /api/receipts/overview` (PR for item 248). It
must be deployed before this is published, or the Receipts tab shows its
error line. Field list: `docs/api-contract.md` "The receipt overview".

**Proven before handing over** (SPA `6ed5015` scratch clone + this exact code,
node-server build, against a LOCAL copy of the 2026-10-07 08:19 backup, zero
live load; 21/21 checks): 378 rows (342 receipts in eight months, 8 set
aside, 28 mail-only: removed, dismissed, held, parked duplicates); "anthr pbc"
23 rows, all Anthropic; "antrhopic" (typo) 46, all Anthropic; "lovbl" 31, all
Lovable; status pill "No matching charge" 26; Source = Upload 193; Upload +
PNG 36; Amount from 1000: 7; Received from 2026-10-01: 16; Reset back to 378;
the viewer opens a receipt; the Emails tab still holds the mail log; filters
survive a reload; no page-level sideways scroll at 400 px; nothing in the table cut off; all nine default
columns fit at 1440 px; zero non-GET requests. `tsc --noEmit` clean.

## Paste this into Lovable

````
Rename the "Email intake" page to "Receipt overview" and give it a receipt
table built with TanStack Table. Make exactly these changes; the code below is
final, copy it as written.

1. Dependencies: add "@tanstack/react-table": "8.21.3" and
   "@tanstack/match-sorter-utils": "8.19.4" to package.json dependencies
   (exact versions, v8, do NOT use v9).

2. src/lib/api.ts: add this block directly after the getInboundLog function.

```ts
// ---------- Receipt overview (every receipt in the tool, one row each) ----------

export type ReceiptOverviewStatus =
  | "matched"
  | "waiting_for_statement"
  | "no_charge"
  | "duplicate"
  | "private"
  | "bill"
  | "settled_outside"
  | "set_aside"
  | "waiting_for_month"
  | "held"
  | "processing"
  | "removed"
  | "dismissed";

export interface ReceiptOverviewRow {
  id: string;
  source: "email" | "upload";
  status: ReceiptOverviewStatus | string;
  review: "ready" | "check" | "pick" | null;
  review_reason: string | null;
  file_name: string;
  /** "pdf" | "png" | "jpg" | ... | "email_body" (a mail text rendered to PDF) | "other" */
  file_type: string;
  document_id: string | null;
  can_view: boolean;
  batch_id: string | null;
  batch_label: string | null;
  batch_type: string | null;
  archive: string | null;
  subject: string | null;
  from_address: string | null;
  submitted_by: string | null;
  received_at: string | null;
  /** "mail" = the mail's arrival; "stored_file" = when the uploaded file was stored. */
  received_from: "mail" | "stored_file" | null;
  receipt_date: string | null;
  vendor: string | null;
  total: string | null;
  amount: number | null;
  currency: string | null;
  card: string | null;
  person: string | null;
  category: string | null;
  reference: string | null;
  note: string | null;
  duplicate_of: string | null;
  pool_month: string | null;
  set_aside_reason: string | null;
}

export interface ReceiptOverviewResponse {
  receipts: ReceiptOverviewRow[];
  n_receipts: number;
  by_status: Record<string, number>;
  by_source: Record<string, number>;
  /** Every status code, in display order. */
  statuses: string[];
  batches: { batch_id: string; label: string; batch_type: string }[];
  generated_at: string | null;
}

export function getReceiptOverview() {
  return apiFetch<ReceiptOverviewResponse>("/api/receipts/overview");
}
```

3. Create src/components/ReceiptOverviewTable.tsx with exactly this content:

```tsx
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import {
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type Column,
  type ColumnDef,
  type ColumnFiltersState,
  type FilterFn,
  type SortingState,
  type VisibilityState,
} from "@tanstack/react-table";
import { rankItem, rankings } from "@tanstack/match-sorter-utils";
import {
  ArrowDown,
  ArrowUp,
  ArrowUpDown,
  Check,
  ChevronLeft,
  ChevronRight,
  FileImage,
  FileText,
  Filter,
  Mail,
  RefreshCw,
  Search,
  Settings2,
  Upload,
  X,
} from "lucide-react";
import { getReceiptOverview, type ReceiptOverviewRow } from "@/lib/api";
import { useLocale, useT, type TKey } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import { ReceiptViewerDialog } from "./ReceiptViewer";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type Row = ReceiptOverviewRow;
type Variant = "text" | "facet" | "dateRange" | "numberRange";
type T = ReturnType<typeof useT>;

declare module "@tanstack/react-table" {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface ColumnMeta<TData, TValue> {
    variant?: Variant;
    /** How a facet value or a cell reads to a person (also what search sees). */
    label?: (value: unknown, row?: Row) => string;
  }
}

const STORE_KEY = "brisken.receiptOverview.v1";

const STATUS_CLASS: Record<string, string> = {
  matched:
    "border-emerald-500/20 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300",
  waiting_for_statement: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  waiting_for_month: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  processing: "border-sky-500/20 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  no_charge: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  held: "border-amber-500/20 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  private: "border-violet-500/20 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  bill: "border-violet-500/20 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  settled_outside:
    "border-violet-500/20 bg-violet-500/10 text-violet-700 dark:text-violet-300",
};

/** Edit distance with swaps (optimal string alignment), stopping above 1. */
function withinOneEdit(a: string, b: string): boolean {
  if (Math.abs(a.length - b.length) > 1) return false;
  const prev2: number[] = [];
  let prev = Array.from({ length: b.length + 1 }, (_, j) => j);
  for (let i = 1; i <= a.length; i++) {
    const cur = [i];
    let rowMin = i;
    for (let j = 1; j <= b.length; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      let v = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        v = Math.min(v, prev2[j - 2] + 1);
      }
      cur[j] = v;
      rowMin = Math.min(rowMin, v);
    }
    if (rowMin > 1) return false;
    prev2.splice(0, prev2.length, ...prev);
    prev = cur;
  }
  return prev[b.length] <= 1;
}

/** How well one query word lands in one field, or -1. */
function rankWord(field: string, word: string): number {
  // Substring, word start, acronym: the strong matches.
  const strong = rankItem(field, word, {
    threshold: word.length < 3 ? rankings.CONTAINS : rankings.ACRONYM,
  });
  if (strong.passed) return strong.rank;
  if (word.length < 3) return -1;
  // Letters in order ("lovbl" -> Lovable), but only when they sit close
  // together: spread across a long subject they match almost anything.
  const loose = rankItem(field, word, { threshold: rankings.MATCHES });
  const maxSpread = Math.ceil(1.5 * (word.length - 1)) + 1;
  if (loose.passed && loose.rank >= rankings.MATCHES + 1 / maxSpread) return loose.rank;
  // One typo in a longer word ("antrhopic", "lovabel").
  if (word.length >= 5) {
    const w = word.toLowerCase();
    for (const token of field.toLowerCase().split(/[^\p{L}\p{N}]+/u)) {
      if (token.length < 4) continue;
      if (withinOneEdit(w, token) || withinOneEdit(w, token.slice(0, w.length))) {
        return rankings.MATCHES;
      }
    }
  }
  return -1;
}

/** Every query word has to land in some field; fields are OR, words are AND. */
function fuzzyMatch(fields: string[], query: string): number | null {
  const words = query.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) return 0;
  let score = 0;
  for (const word of words) {
    let best = -1;
    for (const f of fields) {
      if (!f) continue;
      const r = rankWord(f, word);
      if (r > best) best = r;
    }
    if (best < 0) return null;
    score += best;
  }
  return score;
}

const fuzzyColumn: FilterFn<Row> = (row, columnId, value) => {
  const meta = row
    .getAllCells()
    .find((c) => c.column.id === columnId)?.column.columnDef.meta;
  const raw = row.getValue(columnId);
  const text = meta?.label ? meta.label(raw, row.original) : String(raw ?? "");
  return fuzzyMatch([text], String(value ?? "")) !== null;
};

const facetFilter: FilterFn<Row> = (row, columnId, value) => {
  const picked = value as string[] | undefined;
  if (!picked || picked.length === 0) return true;
  return picked.includes(String(row.getValue(columnId) ?? ""));
};

const dateRangeFilter: FilterFn<Row> = (row, columnId, value) => {
  const [from, to] = (value as [string?, string?]) ?? [];
  const day = String(row.getValue(columnId) ?? "").slice(0, 10);
  if (!from && !to) return true;
  if (!day) return false;
  if (from && day < from) return false;
  if (to && day > to) return false;
  return true;
};

const numberRangeFilter: FilterFn<Row> = (row, columnId, value) => {
  const [min, max] = (value as [number?, number?]) ?? [];
  const n = row.getValue(columnId) as number | null;
  if (min == null && max == null) return true;
  if (n == null) return false;
  if (min != null && n < min) return false;
  if (max != null && n > max) return false;
  return true;
};

const FILTER_FNS = {
  text: fuzzyColumn,
  facet: facetFilter,
  dateRange: dateRangeFilter,
  numberRange: numberRangeFilter,
} as const;

function fmtDate(v: string | null | undefined, locale: string, withTime = false) {
  if (!v) return "";
  const d = new Date(v.length === 10 ? `${v}T12:00:00` : v);
  if (Number.isNaN(d.getTime())) return v;
  return d.toLocaleString(locale, {
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}

function fmtAmount(row: Row, locale: string) {
  if (row.amount == null) return row.total ?? "";
  const n = row.amount.toLocaleString(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return row.currency ? `${n} ${row.currency}` : n;
}

function keyLabel(t: T, prefix: string, code: unknown) {
  const s = String(code ?? "");
  if (!s) return "-";
  const key = `${prefix}.${s}`;
  const out = t(key as TKey);
  return out === key ? s : out;
}

function fileTypeLabel(t: T, code: unknown) {
  const s = String(code ?? "");
  if (s === "email_body") return t("rov.type.email_body");
  if (s === "other") return t("rov.type.other");
  return s.toUpperCase();
}

function fileLabel(t: T, row: Row) {
  return row.file_type === "email_body" ? t("rov.file.emailText") : row.file_name;
}

function loadState(): Partial<{
  filters: ColumnFiltersState;
  sorting: SortingState;
  visibility: VisibilityState;
  query: string;
  pageSize: number;
}> {
  try {
    return JSON.parse(window.localStorage.getItem(STORE_KEY) ?? "{}");
  } catch {
    return {};
  }
}

const DEFAULT_HIDDEN: VisibilityState = {
  file_type: false,
  submitted_by: false,
  currency: false,
  review: false,
  card: false,
  person: false,
  category: false,
  reference: false,
  note: false,
};

export function ReceiptOverviewTable() {
  const t = useT();
  const locale = useLocale();
  const saved = useMemo(loadState, []);
  const [query, setQuery] = useState(saved.query ?? "");
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>(saved.filters ?? []);
  const [sorting, setSorting] = useState<SortingState>(saved.sorting ?? []);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>(
    saved.visibility ?? DEFAULT_HIDDEN,
  );
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: saved.pageSize ?? 50 });
  const [viewing, setViewing] = useState<Row | null>(null);

  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ["receipt-overview"],
    queryFn: getReceiptOverview,
    retry: false,
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(
        STORE_KEY,
        JSON.stringify({
          filters: columnFilters,
          sorting,
          visibility: columnVisibility,
          query,
          pageSize: pagination.pageSize,
        }),
      );
    } catch {
      /* storage blocked: the page works without it */
    }
  }, [columnFilters, sorting, columnVisibility, query, pagination.pageSize]);

  const columns = useMemo<ColumnDef<Row>[]>(
    () => [
      {
        id: "received_at",
        accessorFn: (r) => r.received_at ?? "",
        header: t("rov.col.received"),
        meta: { variant: "dateRange", label: (v) => fmtDate(String(v ?? ""), locale, true) },
        cell: ({ row }) => {
          const v = row.original.received_at;
          const time = v
            ? new Date(v).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" })
            : "";
          return (
            <span
              className="block whitespace-nowrap tabular-nums"
              title={
                row.original.received_from === "stored_file" ? t("rov.received.stored") : undefined
              }
            >
              {fmtDate(v, locale) || "-"}
              {time ? <span className="block text-[11px] text-muted-foreground">{time}</span> : null}
            </span>
          );
        },
      },
      {
        id: "source",
        accessorFn: (r) => r.source,
        header: t("rov.col.source"),
        meta: { variant: "facet", label: (v) => keyLabel(t, "rov.source", v) },
        cell: ({ row }) => (
          <div className="min-w-0">
            <span className="inline-flex items-center gap-1.5 whitespace-nowrap">
              {row.original.source === "email" ? (
                <Mail className="h-3.5 w-3.5 text-muted-foreground" />
              ) : (
                <Upload className="h-3.5 w-3.5 text-muted-foreground" />
              )}
              {keyLabel(t, "rov.source", row.original.source)}
            </span>
            {row.original.submitted_by ? (
              <span className="block max-w-[12rem] break-words text-[11px] text-muted-foreground">
                {row.original.submitted_by}
              </span>
            ) : null}
          </div>
        ),
      },
      {
        id: "file_name",
        accessorFn: (r) => r.file_name,
        header: t("rov.col.file"),
        meta: { variant: "text", label: (_v, r) => (r ? fileLabel(t, r) : "") },
        cell: ({ row }) => {
          const r = row.original;
          const Icon = r.file_type === "pdf" || r.file_type === "email_body" ? FileText : FileImage;
          const viewable = r.can_view && !!r.batch_id && !!r.document_id;
          return (
            <span className="flex min-w-0 max-w-[12rem] items-start gap-1.5">
              <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              {viewable ? (
                <button
                  type="button"
                  className="min-w-0 break-words text-left text-primary underline-offset-2 hover:underline"
                  title={r.file_name}
                  onClick={() => setViewing(r)}
                >
                  {fileLabel(t, r)}
                </button>
              ) : (
                <span className="min-w-0 break-words" title={r.file_name}>
                  {fileLabel(t, r)}
                </span>
              )}
            </span>
          );
        },
      },
      {
        id: "file_type",
        accessorFn: (r) => r.file_type,
        header: t("rov.col.type"),
        meta: { variant: "facet", label: (v) => fileTypeLabel(t, v) },
        cell: ({ row }) => (
          <Badge variant="outline" className="whitespace-nowrap font-normal text-muted-foreground">
            {fileTypeLabel(t, row.original.file_type)}
          </Badge>
        ),
      },
      {
        id: "subject",
        accessorFn: (r) => r.subject ?? "",
        header: t("rov.col.subject"),
        meta: { variant: "text" },
        cell: ({ row }) => (
          <span className="block max-w-[13rem] break-words" title={row.original.subject ?? ""}>
            {row.original.subject || <span className="text-muted-foreground">-</span>}
          </span>
        ),
      },
      {
        id: "vendor",
        accessorFn: (r) => r.vendor ?? "",
        header: t("rov.col.vendor"),
        meta: { variant: "text" },
        cell: ({ row }) => (
          <span className="block max-w-[10rem] break-words font-medium" title={row.original.vendor ?? ""}>
            {row.original.vendor || <span className="font-normal text-muted-foreground">-</span>}
          </span>
        ),
      },
      {
        id: "receipt_date",
        accessorFn: (r) => r.receipt_date ?? "",
        header: t("rov.col.receiptDate"),
        meta: { variant: "dateRange", label: (v) => fmtDate(String(v ?? ""), locale) },
        cell: ({ row }) => (
          <span className="whitespace-nowrap tabular-nums">
            {fmtDate(row.original.receipt_date, locale) || (
              <span className="text-muted-foreground">-</span>
            )}
          </span>
        ),
      },
      {
        id: "amount",
        accessorFn: (r) => r.amount ?? undefined,
        header: t("rov.col.amount"),
        sortUndefined: "last",
        meta: { variant: "numberRange", label: (_v, r) => (r ? fmtAmount(r, locale) : "") },
        cell: ({ row }) => (
          <span className="block whitespace-nowrap text-right tabular-nums">
            {fmtAmount(row.original, locale) || <span className="text-muted-foreground">-</span>}
          </span>
        ),
      },
      {
        id: "currency",
        accessorFn: (r) => r.currency ?? "",
        header: t("rov.col.currency"),
        meta: { variant: "facet", label: (v) => String(v || "-") },
      },
      {
        id: "status",
        accessorFn: (r) => r.status,
        header: t("rov.col.status"),
        meta: { variant: "facet", label: (v) => keyLabel(t, "rov.status", v) },
        cell: ({ row }) => (
          <Badge
            variant="outline"
            className={cn(
              "font-medium",
              STATUS_CLASS[row.original.status] ?? "text-muted-foreground",
            )}
            title={row.original.note ?? undefined}
          >
            {keyLabel(t, "rov.status", row.original.status)}
          </Badge>
        ),
      },
      {
        id: "batch_label",
        accessorFn: (r) => r.batch_label ?? "",
        header: t("rov.col.month"),
        meta: { variant: "facet", label: (v) => String(v || "-") },
        cell: ({ row }) => {
          const r = row.original;
          if (r.batch_id && r.batch_label) {
            return (
              <Link
                to="/expenses/$batchId"
                params={{ batchId: r.batch_id }}
                className="text-primary hover:underline"
              >
                {r.batch_label}
              </Link>
            );
          }
          return (
            <span className="text-muted-foreground">{r.pool_month || "-"}</span>
          );
        },
      },
      {
        id: "submitted_by",
        accessorFn: (r) => [r.submitted_by, r.from_address].filter(Boolean).join(" "),
        header: t("rov.col.submittedBy"),
        meta: { variant: "text" },
      },
      {
        id: "review",
        accessorFn: (r) => r.review ?? "",
        header: t("rov.col.review"),
        meta: { variant: "facet", label: (v) => keyLabel(t, "rov.review", v) },
        cell: ({ row }) => keyLabel(t, "rov.review", row.original.review),
      },
      {
        id: "card",
        accessorFn: (r) => r.card ?? "",
        header: t("rov.col.card"),
        meta: { variant: "facet", label: (v) => String(v || "-") },
      },
      {
        id: "person",
        accessorFn: (r) => r.person ?? "",
        header: t("rov.col.person"),
        meta: { variant: "facet", label: (v) => String(v || "-") },
      },
      {
        id: "category",
        accessorFn: (r) => r.category ?? "",
        header: t("rov.col.category"),
        meta: { variant: "text" },
      },
      {
        id: "reference",
        accessorFn: (r) => r.reference ?? "",
        header: t("rov.col.reference"),
        meta: { variant: "text" },
      },
      {
        id: "note",
        accessorFn: (r) =>
          [r.note, r.set_aside_reason, r.duplicate_of].filter(Boolean).join(" · "),
        header: t("rov.col.note"),
        meta: { variant: "text" },
        cell: ({ getValue }) => (
          <span className="block max-w-[16rem] break-words" title={String(getValue() ?? "")}>
            {String(getValue() ?? "") || "-"}
          </span>
        ),
      },
    ],
    [t, locale],
  );

  // Search runs first, over every column as a person reads it, so the
  // filter counts and the page both follow the search.
  const searched = useMemo(() => {
    const rows = data?.receipts ?? [];
    if (!query.trim()) return rows;
    const scored: { r: Row; s: number }[] = [];
    for (const r of rows) {
      const fields = [
        fileLabel(t, r),
        r.file_name,
        r.subject ?? "",
        r.vendor ?? "",
        r.submitted_by ?? "",
        r.from_address ?? "",
        r.batch_label ?? "",
        r.total ?? "",
        fmtAmount(r, locale),
        r.currency ?? "",
        r.receipt_date ?? "",
        fmtDate(r.receipt_date, locale),
        fmtDate(r.received_at, locale),
        keyLabel(t, "rov.status", r.status),
        keyLabel(t, "rov.source", r.source),
        fileTypeLabel(t, r.file_type),
        r.card ?? "",
        r.person ?? "",
        r.category ?? "",
        r.reference ?? "",
        r.note ?? "",
        r.duplicate_of ?? "",
      ];
      const s = fuzzyMatch(fields, query);
      if (s !== null) scored.push({ r, s });
    }
    return scored.sort((a, b) => b.s - a.s).map((x) => x.r);
  }, [data, query, t, locale]);

  const withFilters = useMemo(
    () =>
      columns.map((c) => ({
        ...c,
        filterFn: FILTER_FNS[(c.meta?.variant ?? "text") as Variant],
      })),
    [columns],
  );

  const table = useReactTable({
    data: searched,
    columns: withFilters,
    state: { columnFilters, sorting, columnVisibility, pagination },
    onColumnFiltersChange: (u) => {
      setColumnFilters(u);
      setPagination((p) => ({ ...p, pageIndex: 0 }));
    },
    onSortingChange: setSorting,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
    autoResetPageIndex: false,
  });

  const nTotal = data?.receipts.length ?? 0;
  const nShown = table.getFilteredRowModel().rows.length;
  const active = columnFilters.length > 0 || query.trim().length > 0;
  const statusCol = table.getColumn("status");
  const statusFilter = (statusCol?.getFilterValue() as string[] | undefined) ?? [];
  const statusCounts = new Map<string, number>();
  for (const r of searched) statusCounts.set(r.status, (statusCounts.get(r.status) ?? 0) + 1);
  const statusOrder = (data?.statuses ?? []).filter((s) => statusCounts.has(s));

  function reset() {
    setQuery("");
    setColumnFilters([]);
    setSorting([]);
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  }

  if (isLoading) {
    return (
      <div className="space-y-2 rounded-md border p-4">
        <Skeleton className="h-8 w-full" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-full" />
        <Skeleton className="h-6 w-2/3" />
      </div>
    );
  }
  if (error) {
    return (
      <div className="rounded-md border p-6 text-sm text-destructive">
        {t("rov.error")} {(error as Error).message}
      </div>
    );
  }

  return (
    <div className="space-y-3" data-receipt-overview>
      {/* Status pills: the at-a-glance count and the quickest filter. */}
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={() => statusCol?.setFilterValue(undefined)}
          className={cn(
            "rounded-full border px-3 py-1 text-xs transition-colors",
            statusFilter.length === 0
              ? "border-foreground/20 bg-foreground text-background"
              : "hover:bg-muted",
          )}
        >
          {t("rov.all")} <span className="tabular-nums opacity-70">{searched.length}</span>
        </button>
        {statusOrder.map((s) => {
          const on = statusFilter.includes(s);
          return (
            <button
              key={s}
              type="button"
              data-status-pill={s}
              onClick={() =>
                statusCol?.setFilterValue(
                  on
                    ? statusFilter.filter((x) => x !== s).length
                      ? statusFilter.filter((x) => x !== s)
                      : undefined
                    : [...statusFilter, s],
                )
              }
              className={cn(
                "rounded-full border px-3 py-1 text-xs transition-colors",
                on ? STATUS_CLASS[s] ?? "bg-muted" : "text-muted-foreground hover:bg-muted",
                on && "ring-1 ring-current",
              )}
            >
              {keyLabel(t, "rov.status", s)}{" "}
              <span className="tabular-nums opacity-70">{statusCounts.get(s)}</span>
            </button>
          );
        })}
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-8"
            onClick={() => refetch()}
            aria-label={t("rov.refresh")}
            title={t("rov.refresh")}
          >
            <RefreshCw className={cn("h-3.5 w-3.5", isFetching && "animate-spin")} />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="h-8">
                <Settings2 className="mr-1.5 h-3.5 w-3.5" />
                {t("rov.columns")}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuLabel>{t("rov.columns.show")}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {table.getAllLeafColumns().map((c) => (
                <DropdownMenuCheckboxItem
                  key={c.id}
                  checked={c.getIsVisible()}
                  onCheckedChange={(v) => c.toggleVisibility(!!v)}
                  onSelect={(e) => e.preventDefault()}
                >
                  {String(c.columnDef.header)}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Toolbar: search, the filters the page is mostly used with, columns. */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-80">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPagination((p) => ({ ...p, pageIndex: 0 }));
            }}
            placeholder={t("rov.search")}
            className="h-9 pl-8 pr-8"
            aria-label={t("rov.search")}
          />
          {query ? (
            <button
              type="button"
              className="absolute right-2 top-2.5 text-muted-foreground hover:text-foreground"
              onClick={() => setQuery("")}
              aria-label={t("rov.clear")}
            >
              <X className="h-4 w-4" />
            </button>
          ) : null}
        </div>
        {(["source", "file_type", "batch_label", "received_at", "receipt_date", "amount", "currency"] as const).map(
          (id) => {
            const col = table.getColumn(id);
            return col ? <FilterChip key={id} column={col} t={t} /> : null;
          },
        )}
        {active ? (
          <Button variant="ghost" size="sm" className="h-9" onClick={reset}>
            <X className="mr-1 h-3.5 w-3.5" />
            {t("rov.reset")}
          </Button>
        ) : null}
      </div>

      <div className="rounded-md border">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader className="sticky top-0 z-10 bg-background">
              {table.getHeaderGroups().map((hg) => (
                <TableRow key={hg.id}>
                  {hg.headers.map((h) => (
                    <TableHead
                      key={h.id}
                      className={cn("whitespace-nowrap", h.column.id === "amount" && "text-right")}
                    >
                      <HeaderCell column={h.column} t={t} />
                    </TableHead>
                  ))}
                </TableRow>
              ))}
            </TableHeader>
            <TableBody>
              {table.getRowModel().rows.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={table.getVisibleLeafColumns().length}
                    className="py-10 text-center text-sm text-muted-foreground"
                  >
                    {nTotal === 0 ? t("rov.empty") : t("rov.noMatch")}
                    {active && nTotal > 0 ? (
                      <Button variant="link" size="sm" onClick={reset}>
                        {t("rov.reset")}
                      </Button>
                    ) : null}
                  </TableCell>
                </TableRow>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <TableRow
                    key={row.id}
                    data-receipt-row={row.original.id}
                    className={cn(
                      ["removed", "dismissed"].includes(row.original.status) &&
                        "text-muted-foreground opacity-70",
                    )}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="py-2 align-top text-sm">
                        {flexRender(cell.column.columnDef.cell ?? ((c) => String(c.getValue() ?? "") || "-"), cell.getContext())}
                      </TableCell>
                    ))}
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Footer: how much of the whole the reader is looking at. */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
        <span data-receipt-count>
          {nShown === nTotal
            ? t("rov.count.all", { n: nTotal })
            : t("rov.count.filtered", { n: nShown, total: nTotal })}
        </span>
        <div className="ml-auto flex items-center gap-2">
          <span>{t("rov.perPage")}</span>
          <Select
            value={String(pagination.pageSize)}
            onValueChange={(v) => setPagination({ pageIndex: 0, pageSize: Number(v) })}
          >
            <SelectTrigger className="h-8 w-20">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[25, 50, 100, 250].map((n) => (
                <SelectItem key={n} value={String(n)}>
                  {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <span className="tabular-nums">
            {t("rov.page", {
              n: table.getPageCount() === 0 ? 0 : pagination.pageIndex + 1,
              total: table.getPageCount(),
            })}
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-8 w-8 p-0"
            disabled={!table.getCanPreviousPage()}
            onClick={() => table.previousPage()}
            aria-label={t("rov.prev")}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-8 w-8 p-0"
            disabled={!table.getCanNextPage()}
            onClick={() => table.nextPage()}
            aria-label={t("rov.next")}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {viewing && viewing.batch_id && viewing.document_id ? (
        <ReceiptViewerDialog
          runId={viewing.batch_id}
          documentId={viewing.document_id}
          fileName={viewing.file_name}
          title={[viewing.vendor, viewing.subject, fileLabel(t, viewing)].filter(Boolean).join(" · ")}
          onClose={() => setViewing(null)}
        />
      ) : null}
    </div>
  );
}

/** Column title: click sorts; the funnel opens that column's own filter. */
function HeaderCell({ column, t }: { column: Column<Row, unknown>; t: T }) {
  const sorted = column.getIsSorted();
  const filtered = column.getIsFiltered();
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1",
        column.id === "amount" && "w-full justify-end",
      )}
    >
      <button
        type="button"
        className="inline-flex items-center gap-1 hover:text-foreground"
        onClick={column.getToggleSortingHandler()}
      >
        {String(column.columnDef.header)}
        {sorted === "asc" ? (
          <ArrowUp className="h-3 w-3" />
        ) : sorted === "desc" ? (
          <ArrowDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-30" />
        )}
      </button>
      <Popover>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label={t("rov.filterColumn", { column: String(column.columnDef.header) })}
            data-column-filter={column.id}
            className={cn(
              "rounded p-0.5 hover:bg-muted",
              filtered ? "text-primary" : "text-muted-foreground/50",
            )}
          >
            <Filter className="h-3 w-3" fill={filtered ? "currentColor" : "none"} />
          </button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-72 p-3">
          <FilterControl column={column} t={t} />
        </PopoverContent>
      </Popover>
    </span>
  );
}

/** The quick-filter buttons in the toolbar; same control as the header's. */
function FilterChip({ column, t }: { column: Column<Row, unknown>; t: T }) {
  const value = column.getFilterValue();
  const meta = column.columnDef.meta;
  let summary = "";
  if (Array.isArray(value) && meta?.variant === "facet" && value.length) {
    summary =
      value.length <= 2
        ? value.map((v) => meta.label?.(v) ?? String(v)).join(", ")
        : t("rov.nSelected", { n: value.length });
  } else if (Array.isArray(value) && (value[0] != null || value[1] != null)) {
    summary = `${value[0] ?? "…"} – ${value[1] ?? "…"}`;
  }
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          data-filter-chip={column.id}
          className={cn("h-9 border-dashed", summary && "border-solid border-primary/40 bg-primary/5")}
        >
          <Filter className="mr-1.5 h-3.5 w-3.5" />
          {String(column.columnDef.header)}
          {summary ? (
            <span className="ml-1.5 max-w-[10rem] break-words rounded bg-primary/10 px-1.5 text-xs font-normal">
              {summary}
            </span>
          ) : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72 p-3">
        <FilterControl column={column} t={t} />
      </PopoverContent>
    </Popover>
  );
}

function FilterControl({ column, t }: { column: Column<Row, unknown>; t: T }) {
  const meta = column.columnDef.meta;
  const variant = meta?.variant ?? "text";
  const value = column.getFilterValue();
  const title = String(column.columnDef.header);

  if (variant === "facet") {
    const picked = new Set((value as string[] | undefined) ?? []);
    const facets = [...column.getFacetedUniqueValues().entries()]
      .map(([v, n]) => ({ v: String(v ?? ""), n: n as number }))
      .sort((a, b) => b.n - a.n);
    return (
      <div className="space-y-2">
        <p className="text-xs font-medium">{title}</p>
        <div className="max-h-64 space-y-0.5 overflow-y-auto">
          {facets.map(({ v, n }) => (
            <label
              key={v || "(empty)"}
              className="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 text-sm hover:bg-muted"
            >
              <Checkbox
                checked={picked.has(v)}
                onCheckedChange={(on) => {
                  const next = new Set(picked);
                  if (on) next.add(v);
                  else next.delete(v);
                  column.setFilterValue(next.size ? [...next] : undefined);
                }}
              />
              <span className="min-w-0 flex-1 break-words">{meta?.label?.(v) ?? (v || "-")}</span>
              <span className="tabular-nums text-xs text-muted-foreground">{n}</span>
              {picked.has(v) ? <Check className="h-3 w-3 text-primary" /> : null}
            </label>
          ))}
        </div>
        {picked.size ? (
          <Button variant="ghost" size="sm" className="h-7 w-full" onClick={() => column.setFilterValue(undefined)}>
            {t("rov.clear")}
          </Button>
        ) : null}
      </div>
    );
  }

  if (variant === "dateRange" || variant === "numberRange") {
    const [a, b] = (value as [unknown, unknown] | undefined) ?? [];
    const isDate = variant === "dateRange";
    const parse = (s: string) => (s === "" ? undefined : isDate ? s : Number(s));
    const set = (next: [unknown, unknown]) =>
      column.setFilterValue(next[0] == null && next[1] == null ? undefined : next);
    return (
      <div className="space-y-2">
        <p className="text-xs font-medium">{title}</p>
        <div className="grid grid-cols-2 gap-2">
          <label className="space-y-1 text-xs text-muted-foreground">
            {isDate ? t("rov.from") : t("rov.min")}
            <Input
              type={isDate ? "date" : "number"}
              step={isDate ? undefined : "0.01"}
              value={a == null ? "" : String(a)}
              onChange={(e) => set([parse(e.target.value), b])}
              className="h-8"
            />
          </label>
          <label className="space-y-1 text-xs text-muted-foreground">
            {isDate ? t("rov.to") : t("rov.max")}
            <Input
              type={isDate ? "date" : "number"}
              step={isDate ? undefined : "0.01"}
              value={b == null ? "" : String(b)}
              onChange={(e) => set([a, parse(e.target.value)])}
              className="h-8"
            />
          </label>
        </div>
        {a != null || b != null ? (
          <Button variant="ghost" size="sm" className="h-7 w-full" onClick={() => column.setFilterValue(undefined)}>
            {t("rov.clear")}
          </Button>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium">{title}</p>
      <Input
        autoFocus
        value={String(value ?? "")}
        onChange={(e) => column.setFilterValue(e.target.value || undefined)}
        placeholder={t("rov.filterText")}
        className="h-8"
      />
      <p className="text-[11px] text-muted-foreground">{t("rov.fuzzyHint")}</p>
    </div>
  );
}
```

4. src/components/InboundLogScreen.tsx:
   - import { ReceiptOverviewTable } from "./ReceiptOverviewTable";
   - import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
   - In InboundLogScreen's return: the <main> becomes
     className="mx-auto w-full max-w-screen-2xl px-4 py-6 sm:px-6"; the page
     title becomes t("rov.title") with t("rov.desc") under it; below the title
     add <Tabs defaultValue="receipts"> with two triggers, "receipts"
     (t("rov.tab.receipts")) and "emails" (t("rov.tab.emails") plus a small
     amber count pill showing data.n_held when it is above 0). The "receipts"
     tab renders <ReceiptOverviewTable />. The "emails" tab holds EVERYTHING
     the page showed before (the badges row with t("mail.desc") as its lead
     text, the retry button, the refusals strip and the mail table), unchanged.
     This diff is exact:

```diff
@@ -44,6 +44,8 @@ import {
 } from "@/components/ui/dropdown-menu";
 import { DashboardHeader } from "./DashboardHeader";
 import { ReceiptViewerDialog } from "./ReceiptViewer";
+import { ReceiptOverviewTable } from "./ReceiptOverviewTable";
+import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
 import { Button } from "@/components/ui/button";
 import { Badge } from "@/components/ui/badge";
 import { Skeleton } from "@/components/ui/skeleton";
@@ -900,12 +902,29 @@ export function InboundLogScreen() {
   return (
     <div className="min-h-screen bg-background">
       <DashboardHeader />
-      <main className="mx-auto w-full max-w-7xl px-6 py-6">
+      <main className="mx-auto w-full max-w-screen-2xl px-4 py-6 sm:px-6">
+        <div>
+          <h1 className="text-lg font-semibold tracking-tight">{t("rov.title")}</h1>
+          <p className="text-sm text-muted-foreground">{t("rov.desc")}</p>
+        </div>
+        <Tabs defaultValue="receipts" className="mt-4">
+          <TabsList>
+            <TabsTrigger value="receipts">{t("rov.tab.receipts")}</TabsTrigger>
+            <TabsTrigger value="emails" className="gap-1.5">
+              {t("rov.tab.emails")}
+              {data && data.n_held > 0 ? (
+                <span className="rounded-full bg-amber-500/15 px-1.5 text-[11px] tabular-nums text-amber-700 dark:text-amber-300">
+                  {data.n_held}
+                </span>
+              ) : null}
+            </TabsTrigger>
+          </TabsList>
+          <TabsContent value="receipts" className="mt-4">
+            <ReceiptOverviewTable />
+          </TabsContent>
+          <TabsContent value="emails" className="mt-4">
         <div className="flex flex-wrap items-center gap-3">
-          <div>
-            <h1 className="text-lg font-semibold tracking-tight">{t("mail.title")}</h1>
-            <p className="text-sm text-muted-foreground">{t("mail.desc")}</p>
-          </div>
+          <p className="text-sm text-muted-foreground">{t("mail.desc")}</p>
           <div className="ml-auto flex flex-wrap items-center gap-2">
             {data && data.n_held > 0 ? (
               <Badge
@@ -1012,6 +1031,8 @@ export function InboundLogScreen() {
             </Table>
           )}
         </div>
+          </TabsContent>
+        </Tabs>
       </main>
     </div>
   );
```

5. src/components/DashboardHeader.tsx: the "/inbound" nav item's label becomes
   t("rov.title") (was t("mail.title")). Keep the Mail icon and the /inbound
   route path.

6. src/routes/inbound.tsx head: title "Receipt overview · Brisken Expense
   Reconciliation", og:title "Receipt overview · Brisken", both descriptions
   "Every receipt in the tool, wherever it came from."

7. src/lib/i18n.tsx: add these keys to the English dictionary (after
   "mail.desc"):

```ts
  // Receipt overview (the page formerly called Email intake)
  "rov.title": "Receipt overview",
  "rov.desc": "Every receipt in the tool, wherever it came from. Search, filter and open any of them.",
  "rov.tab.receipts": "Receipts",
  "rov.tab.emails": "Emails",
  "rov.all": "All",
  "rov.search": "Search vendor, file, subject, sender...",
  "rov.clear": "Clear",
  "rov.reset": "Reset filters",
  "rov.refresh": "Refresh",
  "rov.columns": "Columns",
  "rov.columns.show": "Show columns",
  "rov.error": "The receipt list could not be loaded.",
  "rov.empty": "No receipts in the tool yet.",
  "rov.noMatch": "No receipt matches these filters.",
  "rov.count.all": "{n} receipts",
  "rov.count.filtered": "{n} of {total} receipts",
  "rov.perPage": "Rows per page",
  "rov.page": "Page {n} of {total}",
  "rov.prev": "Previous page",
  "rov.next": "Next page",
  "rov.from": "From",
  "rov.to": "To",
  "rov.min": "Min",
  "rov.max": "Max",
  "rov.nSelected": "{n} selected",
  "rov.filterColumn": "Filter {column}",
  "rov.filterText": "Type to filter...",
  "rov.fuzzyHint": "Close matches count: \"anthr pbc\" finds Anthropic, PBC.",
  "rov.received.stored": "Uploaded: the time the file was stored",
  "rov.file.emailText": "Email text",
  "rov.col.received": "Received",
  "rov.col.source": "Source",
  "rov.col.file": "File",
  "rov.col.type": "File type",
  "rov.col.subject": "Subject",
  "rov.col.vendor": "Vendor",
  "rov.col.receiptDate": "Receipt date",
  "rov.col.amount": "Amount",
  "rov.col.currency": "Currency",
  "rov.col.status": "Status",
  "rov.col.month": "Month",
  "rov.col.submittedBy": "Sent by",
  "rov.col.review": "Review",
  "rov.col.card": "Card",
  "rov.col.person": "Company / person",
  "rov.col.category": "Account",
  "rov.col.reference": "Reference",
  "rov.col.note": "Note",
  "rov.source.email": "Email",
  "rov.source.upload": "Upload",
  "rov.type.email_body": "Email text",
  "rov.type.other": "Other",
  "rov.review.ready": "Ready",
  "rov.review.check": "Needs a look",
  "rov.review.pick": "Pick a match",
  "rov.status.matched": "Matched to a charge",
  "rov.status.waiting_for_statement": "Waiting for statement",
  "rov.status.no_charge": "No matching charge",
  "rov.status.duplicate": "Duplicate copy",
  "rov.status.private": "Private",
  "rov.status.bill": "Paid by transfer",
  "rov.status.settled_outside": "Settled outside the card",
  "rov.status.set_aside": "Set aside (not a receipt)",
  "rov.status.waiting_for_month": "Waiting for its month",
  "rov.status.held": "Held",
  "rov.status.processing": "Being read",
  "rov.status.removed": "Removed",
  "rov.status.dismissed": "Dismissed",
```

   and these to the Portuguese dictionary (after its "mail.desc"):

```ts
  // Receipt overview
  "rov.title": "Visão geral dos recibos",
  "rov.desc": "Todos os recibos da ferramenta, venham de onde vierem. Pesquise, filtre e abra qualquer um.",
  "rov.tab.receipts": "Recibos",
  "rov.tab.emails": "Emails",
  "rov.all": "Todos",
  "rov.search": "Pesquisar fornecedor, arquivo, assunto...",
  "rov.clear": "Limpar",
  "rov.reset": "Limpar filtros",
  "rov.refresh": "Atualizar",
  "rov.columns": "Colunas",
  "rov.columns.show": "Mostrar colunas",
  "rov.error": "Não foi possível carregar a lista de recibos.",
  "rov.empty": "Ainda não há recibos na ferramenta.",
  "rov.noMatch": "Nenhum recibo corresponde a estes filtros.",
  "rov.count.all": "{n} recibos",
  "rov.count.filtered": "{n} de {total} recibos",
  "rov.perPage": "Linhas por página",
  "rov.page": "Página {n} de {total}",
  "rov.prev": "Página anterior",
  "rov.next": "Próxima página",
  "rov.from": "De",
  "rov.to": "Até",
  "rov.min": "Mín.",
  "rov.max": "Máx.",
  "rov.nSelected": "{n} selecionados",
  "rov.filterColumn": "Filtrar {column}",
  "rov.filterText": "Digite para filtrar...",
  "rov.fuzzyHint": "Aproximações contam: \"anthr pbc\" encontra Anthropic, PBC.",
  "rov.received.stored": "Enviado: quando o arquivo foi guardado",
  "rov.file.emailText": "Texto do email",
  "rov.col.received": "Recebido",
  "rov.col.source": "Origem",
  "rov.col.file": "Arquivo",
  "rov.col.type": "Tipo de arquivo",
  "rov.col.subject": "Assunto",
  "rov.col.vendor": "Fornecedor",
  "rov.col.receiptDate": "Data do recibo",
  "rov.col.amount": "Valor",
  "rov.col.currency": "Moeda",
  "rov.col.status": "Status",
  "rov.col.month": "Mês",
  "rov.col.submittedBy": "Enviado por",
  "rov.col.review": "Revisão",
  "rov.col.card": "Cartão",
  "rov.col.person": "Empresa / pessoa",
  "rov.col.category": "Conta",
  "rov.col.reference": "Referência",
  "rov.col.note": "Nota",
  "rov.source.email": "Email",
  "rov.source.upload": "Upload",
  "rov.type.email_body": "Texto do email",
  "rov.type.other": "Outro",
  "rov.review.ready": "Pronto",
  "rov.review.check": "Precisa de atenção",
  "rov.review.pick": "Escolher par",
  "rov.status.matched": "Ligado a uma cobrança",
  "rov.status.waiting_for_statement": "Aguardando extrato",
  "rov.status.no_charge": "Sem cobrança correspondente",
  "rov.status.duplicate": "Cópia duplicada",
  "rov.status.private": "Particular",
  "rov.status.bill": "Pago por transferência",
  "rov.status.settled_outside": "Liquidado fora do cartão",
  "rov.status.set_aside": "Separado (não é recibo)",
  "rov.status.waiting_for_month": "Aguardando o mês",
  "rov.status.held": "Retido",
  "rov.status.processing": "Em leitura",
  "rov.status.removed": "Removido",
  "rov.status.dismissed": "Descartado",
```

Do not change any other screen. Do not change the mail log's behaviour.
````

## Verify after publish

1. Bundle: the published chunks name `/api/receipts/overview`, `rov.status.no_charge`
   and `data-receipt-overview`.
2. Drive cold from the login gate, read-only, replaying the overview payload
   (one GET, `route.fulfill` after that, every non-GET aborted): the page h1
   reads "Receipt overview", the nav link to `/inbound` reads the same, the
   footer `[data-receipt-count]` equals `n_receipts`, a status pill narrows to
   that status's `by_status` count, and the Emails tab still lists mails.
3. Then move this row to Applied in `PROMPT-STATUS.md`.
