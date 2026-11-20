import * as React from "react";
import { useEffect, useRef, useState } from "react";
import { Download, Upload, X } from "lucide-react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "../lib/api";
import { formatINR, toPaise } from "../lib/currency-display";
import { indiaBusinessDate } from "../lib/business-date";
import { toast } from "sonner";

type Item = {
  id: string;
  item_code: string;
  purchase_date: string;
  purchase_price_paise: number;
  notes?: string | null;
  current_status: string;
  version: number;
  age_days?: number | null;
};
type Page = { items: Item[]; next_cursor: string | null; has_more: boolean };
type Event = {
  id: string;
  event_type: string;
  event_date: string;
  reason?: string | null;
};
type ImportError = { row: number; message: string };
type ImportPreview = {
  rows: Record<string, string>[];
  errors: ImportError[];
  warnings: ImportError[];
  total_rows: number;
  ready: boolean;
};

function Age({ days }: { days?: number | null }) {
  if (days == null) return null;
  const tone = days >= 90 ? "danger" : days >= 60 ? "warning" : "badge";
  return <span className={tone}>{days}d old</span>;
}
function stripModalCancelButtons(node: React.ReactNode): React.ReactNode {
  return React.Children.map(node, (child) => {
    if (!React.isValidElement(child)) return child;
    if (
      child.type === "button" &&
      typeof child.props.children === "string" &&
      child.props.children.trim() === "Cancel"
    )
      return null;
    return child.props.children
      ? React.cloneElement(
          child,
          undefined,
          stripModalCancelButtons(child.props.children),
        )
      : child;
  });
}
function Dialog({
  title,
  children,
  close,
}: {
  title: string;
  children: React.ReactNode;
  close: () => void;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="inventory-dialog-title"
      >
        <div className="modal-heading">
          <h2 id="inventory-dialog-title">{title}</h2>
          <button className="icon-button" onClick={close} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        {stripModalCancelButtons(children)}
      </section>
    </div>
  );
}
function downloadImportTemplate() {
  const csv =
    "item_code,purchase_date,purchase_price_paise,notes,status,sold_date\nABC-001,2026-11-20,12500,Example item,IN_STOCK,\n";
  const url = URL.createObjectURL(
    new Blob([csv], { type: "text/csv;charset=utf-8" }),
  );
  const link = document.createElement("a");
  link.href = url;
  link.download = "inventory-import-template.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export function InventoryPage({ online }: { online: boolean }) {
  const [code, setCode] = useState("");
  const [notes, setNotes] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [date, setDate] = useState(indiaBusinessDate);
  const [price, setPrice] = useState("");
  const [selected, setSelected] = useState<Item | null>(null);
  const [editing, setEditing] = useState<Item | null>(null);
  const [action, setAction] = useState<"return" | "reverse" | null>(null);
  const [reason, setReason] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [importOpen, setImportOpen] = useState(false);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const loadMoreRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();
  useEffect(() => {
    const t = window.setTimeout(() => setSearch(searchInput.trim()), 250);
    return () => window.clearTimeout(t);
  }, [searchInput]);
  const inventory = useInfiniteQuery({
    queryKey: ["inventory", search, status],
    initialPageParam: "",
    queryFn: ({ pageParam, signal }) =>
      api<Page>(
        `/api/v1/inventory?limit=25${search ? `&search=${encodeURIComponent(search)}` : ""}${status ? `&status=${status}` : ""}${pageParam ? `&cursor=${encodeURIComponent(pageParam)}` : ""}`,
        { signal },
      ),
    getNextPageParam: (p) => (p.has_more ? p.next_cursor : undefined),
  });
  useEffect(() => {
    const target = loadMoreRef.current;
    if (!target || !inventory.hasNextPage) return;
    const o = new IntersectionObserver(
      (e) => {
        if (e[0].isIntersecting && !inventory.isFetchingNextPage)
          inventory.fetchNextPage();
      },
      { rootMargin: "240px" },
    );
    o.observe(target);
    return () => o.disconnect();
  }, [
    inventory.hasNextPage,
    inventory.isFetchingNextPage,
    inventory.fetchNextPage,
  ]);
  const items = inventory.data?.pages.flatMap((p) => p.items) ?? [];
  const save = useMutation({
    mutationFn: () =>
      api("/api/v1/inventory", {
        method: "POST",
        body: JSON.stringify({
          item_code: code,
          purchase_date: date,
          purchase_price_paise: toPaise(price),
          notes: notes || null,
        }),
      }),
    onSuccess: () => {
      setCode("");
      setPrice("");
      setNotes("");
      qc.invalidateQueries({ queryKey: ["inventory"] });
      toast.success("Inventory item added");
    },
  });
  const update = useMutation({
    mutationFn: () =>
      api(`/api/v1/inventory/${editing!.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          item_code: code,
          purchase_date: date,
          purchase_price_paise: toPaise(price),
          notes: notes || null,
          expected_version: editing!.version,
        }),
      }),
    onSuccess: () => {
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["inventory"] });
      toast.success("Inventory item updated");
    },
  });
  const sell = useMutation({
    mutationFn: (item: Item) =>
      api(`/api/v1/inventory/${item.id}/sell`, {
        method: "POST",
        body: JSON.stringify({
          sold_date: indiaBusinessDate(),
          expected_version: item.version,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["inventory"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Item marked sold");
    },
  });
  const change = useMutation({
    mutationFn: () =>
      api(
        `/api/v1/inventory/${selected!.id}/${action === "return" ? "return" : "reverse-sale"}`,
        {
          method: "POST",
          body: JSON.stringify(
            action === "return"
              ? {
                  return_date: indiaBusinessDate(),
                  reason: reason || null,
                  expected_version: selected!.version,
                }
              : {
                  reversal_date: indiaBusinessDate(),
                  reason,
                  expected_version: selected!.version,
                },
          ),
        },
      ),
    onSuccess: () => {
      setAction(null);
      setSelected(null);
      setReason("");
      qc.invalidateQueries({ queryKey: ["inventory"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success(
        action === "return" ? "Item returned to stock" : "Sale reversed",
      );
    },
  });
  const history = useQuery({
    queryKey: ["inventory-history", selected?.id],
    queryFn: () => api<Event[]>(`/api/v1/inventory/${selected!.id}/history`),
    enabled: !!selected,
  });
  const previewImport = async () => {
    if (!file) return;
    setPreviewBusy(true);
    try {
      const body = new FormData();
      body.append("file", file);
      setPreview(
        await api<ImportPreview>("/api/v1/inventory/import/preview", {
          method: "POST",
          body,
        }),
      );
      setImportOpen(false);
    } catch (error) {
      toast.error((error as Error).message);
    } finally {
      setPreviewBusy(false);
    }
  };
  const commitImport = useMutation({
    mutationFn: () =>
      api("/api/v1/inventory/import/commit", {
        method: "POST",
        body: JSON.stringify({ filename: file?.name, rows: preview?.rows }),
      }),
    onSuccess: () => {
      setPreview(null);
      setFile(null);
      qc.invalidateQueries({ queryKey: ["inventory"] });
      toast.success("Import committed");
    },
  });
  const openEdit = (item: Item) => {
    setEditing(item);
    setCode(item.item_code);
    setDate(item.purchase_date);
    setPrice(Math.round(item.purchase_price_paise / 100).toString());
    setNotes(item.notes ?? "");
  };
  const openHistory = (item: Item) => {
    setEditing(null);
    setSelected(item);
  };
  return (
    <>
      <form
        className="card form"
        onSubmit={(e) => {
          e.preventDefault();
          if (online) save.mutate();
        }}
      >
        <h2>Add inventory item</h2>
        <label>
          Item code
          <input
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
        </label>
        <label>
          Purchase date
          <input
            type="date"
            value={date}
            onChange={(e) => setDate(e.target.value)}
            required
          />
        </label>
        <label>
          Purchase price
          <input
            inputMode="numeric"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="0"
            required
          />
        </label>
        <label>
          Notes (optional)
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
          />
        </label>
        <button className="primary" disabled={!online || save.isPending}>
          {save.isPending ? "Savingâ€¦" : "Add item"}
        </button>
      </form>
      <div className="toolbar">
        <label className="search-field">
          Search
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Item code"
          />
        </label>
        <label>
          Status
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="IN_STOCK">In stock</option>
            <option value="SOLD">Sold</option>
          </select>
        </label>
        <button
          className="secondary toolbar-action"
          type="button"
          disabled={!online}
          onClick={() => setImportOpen(true)}
        >
          <Upload size={16} />
          Import
        </button>
        <a
          className="secondary toolbar-action"
          href={`/api/v1/inventory/export${status ? `?status=${status}` : ""}`}
        >
          <Download size={16} />
          Export
        </a>
      </div>
      <section className="card">
        <div className="section-heading">
          <h2>Items</h2>
          <span className="muted">{items.length} shown</span>
        </div>
        {inventory.error ? (
          <p className="error" role="alert">
            {(inventory.error as Error).message}
          </p>
        ) : inventory.isLoading ? (
          <p className="muted">Loading inventoryâ€¦</p>
        ) : items.length === 0 ? (
          <p className="muted">No matching inventory.</p>
        ) : (
          items.map((item) => (
            <div
              className="list-row list-button"
              role="button"
              tabIndex={0}
              key={item.id}
              onClick={() => openEdit(item)}
              onKeyDown={(e) => e.key === "Enter" && openEdit(item)}
            >
              <div>
                <strong>{item.item_code}</strong>
                <small>
                  {item.purchase_date} · {formatINR(item.purchase_price_paise)}{" "}
                  {item.notes ? `· ${item.notes}` : ""}
                </small>
                <Age days={item.age_days} />
              </div>
              <span className="row-end">
                {item.current_status === "IN_STOCK" ? (
                  <button
                    className="secondary"
                    disabled={!online}
                    onClick={(e) => {
                      e.stopPropagation();
                      sell.mutate(item);
                    }}
                  >
                    Mark sold
                  </button>
                ) : (
                  <span className="badge">Sold</span>
                )}
              </span>
            </div>
          ))
        )}
        <div ref={loadMoreRef} className="load-more">
          {inventory.hasNextPage ? "Scroll to load more" : "End of inventory"}
        </div>
      </section>
      {importOpen && (
        <Dialog title="Import inventory CSV" close={() => setImportOpen(false)}>
          <div className="form">
            <div className="import-help">
              <p className="muted">Select a CSV file to import.</p>
              <button
                className="secondary template-download"
                type="button"
                onClick={downloadImportTemplate}
              >
                <Download size={16} />
                Download template
              </button>
            </div>
            <label className="file-picker secondary">
              <Upload size={16} />
              Browse
              <input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
            <span className="muted">{file?.name || "No file selected"}</span>
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setImportOpen(false)}
              >
                Cancel
              </button>
              <button
                className="primary"
                type="button"
                disabled={!file || previewBusy || !online}
                onClick={previewImport}
              >
                {previewBusy ? "Loading previewâ€¦" : "Preview"}
              </button>
            </div>
          </div>
        </Dialog>
      )}
      {preview && (
        <Dialog title="Import preview" close={() => setPreview(null)}>
          <div className="form">
            <div className="import-summary">
              <strong>{file?.name || "inventory.csv"}</strong>
              <span className="muted">
                {preview.total_rows} rows found ·{" "}
                {preview.rows.length - preview.errors.length} valid ·{" "}
                {preview.errors.length} error
                {preview.errors.length === 1 ? "" : "s"}
              </span>
            </div>
            <div className="import-preview-list">
              {preview.rows.map((row, index) => {
                const error = preview.errors.find(
                  (item) => item.row === index + 2,
                );
                return (
                  <div
                    className={`import-preview-row ${error ? "has-error" : ""}`}
                    key={`${row.item_code || "row"}-${index}`}
                  >
                    <span>Row {index + 2}</span>
                    <strong>{row.item_code || "â€”"}</strong>
                    <span>{row.purchase_date || "â€”"}</span>
                    <span>
                      {row.purchase_price_paise
                        ? formatINR(Number(row.purchase_price_paise))
                        : "â€”"}
                    </span>
                    <span>{error?.message || "Valid"}</span>
                  </div>
                );
              })}
            </div>
            {preview.errors.length > 0 && (
              <p className="error" role="alert">
                Fix the CSV errors before importing.
              </p>
            )}
            {preview.warnings.length > 0 && (
              <p className="warning-panel">
                {preview.warnings.length} warning
                {preview.warnings.length === 1 ? "" : "s"} found.
              </p>
            )}
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setPreview(null)}
              >
                Cancel
              </button>
              <button
                className="primary"
                type="button"
                disabled={!preview.ready || commitImport.isPending || !online}
                onClick={() => commitImport.mutate()}
              >
                {commitImport.isPending
                  ? "Importingâ€¦"
                  : `Import ${preview.rows.length} valid row${preview.rows.length === 1 ? "" : "s"}`}
              </button>
            </div>
          </div>
        </Dialog>
      )}
      {editing && (
        <Dialog
          title={`Edit ${editing.item_code}`}
          close={() => setEditing(null)}
        >
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              if (online) update.mutate();
            }}
          >
            <label>
              Item code
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />
            </label>
            <label>
              Purchase date
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                required
              />
            </label>
            <label>
              Purchase price
              <input
                inputMode="numeric"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                required
              />
            </label>
            <label>
              Notes (optional)
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
              />
            </label>
            {update.error && (
              <p className="error" role="alert">
                {(update.error as Error).message}
              </p>
            )}
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => openHistory(editing)}
              >
                View history
              </button>
              <button
                className="secondary"
                type="button"
                onClick={() => setEditing(null)}
                disabled={update.isPending}
              >
                Cancel
              </button>
              <button
                className="primary"
                type="submit"
                disabled={!online || update.isPending}
              >
                {update.isPending ? "Savingâ€¦" : "Save changes"}
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {selected && (
        <Dialog
          title={`${selected.item_code} history`}
          close={() => {
            setSelected(null);
            setAction(null);
          }}
        >
          <p className="muted">
            {selected.notes || "No notes"} · <Age days={selected.age_days} />
          </p>
          {history.data?.map((event) => (
            <div className="list-row" key={event.id}>
              <span>{event.event_date}</span>
              <span>
                {event.event_type.replaceAll("_", " ")}
                {event.reason ? ` · ${event.reason}` : ""}
              </span>
            </div>
          ))}
          {selected.current_status === "SOLD" && !action && (
            <div className="dialog-actions">
              <button
                className="secondary"
                disabled={!online}
                onClick={() => setAction("return")}
              >
                Mark returned
              </button>
              <button
                className="danger"
                disabled={!online}
                onClick={() => setAction("reverse")}
              >
                Reverse sale
              </button>
            </div>
          )}
          {action && (
            <div className="form">
              <label>
                Reason{action === "reverse" && " (required)"}
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  required={action === "reverse"}
                  rows={3}
                />
              </label>
              <div className="dialog-actions">
                <button className="secondary" onClick={() => setAction(null)}>
                  Cancel
                </button>
                <button
                  className="primary"
                  disabled={
                    change.isPending || (action === "reverse" && !reason.trim())
                  }
                  onClick={() => change.mutate()}
                >
                  {change.isPending
                    ? "Savingâ€¦"
                    : action === "return"
                      ? "Confirm return"
                      : "Confirm reversal"}
                </button>
              </div>
            </div>
          )}
        </Dialog>
      )}
    </>
  );
}
