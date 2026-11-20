import { FormEvent, useState } from "react";
import { AlertCircle, Pause, Play } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "../lib/api";
import { formatINR, toPaise } from "../lib/currency-display";
import { indiaBusinessDate, indiaBusinessMonth } from "../lib/business-date";
import {
  BusyButton,
  ConfirmDialog,
  EmptyState,
  Modal,
  Page,
  SkeletonBlock,
} from "../components/app-ui";

type Sale = {
  id: string;
  sale_date: string;
  amount_paise: number;
  version?: number;
};
type RecurringExpense = {
  id: string;
  expense_name: string;
  category: string;
  amount_paise: number;
  effective_start_month: string;
  effective_end_month: string | null;
  is_active: boolean;
  paused_from_month: string | null;
  resumed_from_month: string | null;
};
type OtherExpense = {
  id: string;
  expense_date: string;
  category: string;
  description: string;
  amount_paise: number;
  version: number;
};

export function Entries({ online }: { online: boolean }) {
  const [tab, setTab] = useState<"sales" | "recurring" | "other">("sales");
  const [date, setDate] = useState(indiaBusinessDate);
  const [amount, setAmount] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Miscellaneous");
  const [description, setDescription] = useState("");
  const [edit, setEdit] = useState<Sale | null>(null);
  const [editRecurring, setEditRecurring] = useState<RecurringExpense | null>(
    null,
  );
  const [editOther, setEditOther] = useState<OtherExpense | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Sale | null>(null);
  const [pauseExpense, setPauseExpense] = useState<RecurringExpense | null>(
    null,
  );
  const [pauseFromMonth, setPauseFromMonth] = useState(indiaBusinessMonth());
  const queryClient = useQueryClient();
  const month = date.slice(0, 7);
  const { data: sales = [], isLoading: salesLoading } = useQuery({
    queryKey: ["sales", month],
    queryFn: () => api<Sale[]>(`/api/v1/sales?month=${month}`),
    enabled: tab === "sales",
  });
  const { data: recurring = [], isLoading: recurringLoading } = useQuery({
    queryKey: ["recurring-expenses"],
    queryFn: () => api<RecurringExpense[]>("/api/v1/recurring-expenses"),
    enabled: tab === "recurring",
  });
  const { data: other = [], isLoading: otherLoading } = useQuery({
    queryKey: ["other-expenses"],
    queryFn: () => api<OtherExpense[]>("/api/v1/expenses"),
    enabled: tab === "other",
  });
  const save = useMutation({
    mutationFn: () => {
      if (tab === "sales")
        return api("/api/v1/sales", {
          method: "POST",
          body: JSON.stringify({
            sale_date: date,
            amount_paise: toPaise(amount),
          }),
        });
      if (tab === "recurring")
        return api("/api/v1/recurring-expenses", {
          method: "POST",
          body: JSON.stringify({
            expense_name: name,
            category,
            amount_paise: toPaise(amount),
            effective_start_month: `${date.slice(0, 7)}-01`,
          }),
        });
      return api("/api/v1/expenses", {
        method: "POST",
        body: JSON.stringify({
          expense_date: date,
          category,
          description,
          amount_paise: toPaise(amount),
        }),
      });
    },
    onSuccess: () => {
      setAmount("");
      setName("");
      setDescription("");
      queryClient.invalidateQueries();
      toast.success("Saved");
    },
  });
  const pause = useMutation({
    mutationFn: () =>
      api(`/api/v1/recurring-expenses/${pauseExpense?.id}/pause`, {
        method: "POST",
        body: JSON.stringify({ pause_from_month: `${pauseFromMonth}-01` }),
      }),
    onSuccess: () => {
      setPauseExpense(null);
      queryClient.invalidateQueries({ queryKey: ["recurring-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Recurring expense paused");
    },
  });
  const resume = useMutation({
    mutationFn: (item: RecurringExpense) =>
      api(`/api/v1/recurring-expenses/${item.id}/resume`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["recurring-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Recurring expense resumed");
    },
  });
  const updateRecurring = useMutation({
    mutationFn: () =>
      api(`/api/v1/recurring-expenses/${editRecurring?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          expense_name: name,
          category,
          amount_paise: toPaise(amount),
          effective_start_month: `${date.slice(0, 7)}-01`,
        }),
      }),
    onSuccess: () => {
      setEditRecurring(null);
      queryClient.invalidateQueries({ queryKey: ["recurring-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Recurring expense updated");
    },
  });
  const updateOther = useMutation({
    mutationFn: () =>
      api(`/api/v1/expenses/${editOther?.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          expense_date: date,
          category,
          description,
          amount_paise: toPaise(amount),
          expected_version: editOther?.version,
        }),
      }),
    onSuccess: () => {
      setEditOther(null);
      queryClient.invalidateQueries({ queryKey: ["other-expenses"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Other expense updated");
    },
  });
  const update = useMutation({
    mutationFn: (sale: Sale) =>
      api(`/api/v1/sales/${sale.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          sale_date: sale.sale_date,
          amount_paise: toPaise(amount),
        }),
      }),
    onSuccess: () => {
      setEdit(null);
      setAmount("");
      queryClient.invalidateQueries({ queryKey: ["sales"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      toast.success("Sales updated");
    },
  });
  const remove = useMutation({
    mutationFn: (sale: Sale) =>
      api(`/api/v1/sales/${sale.id}`, { method: "DELETE" }),
    onSuccess: () => {
      setConfirmDelete(null);
      queryClient.invalidateQueries();
      toast.success("Sales record deleted");
    },
  });
  const openSale = (sale: Sale) => {
    setEdit(sale);
    setDate(sale.sale_date);
    setAmount(Math.round(sale.amount_paise / 100).toString());
  };
  const openRecurring = (item: RecurringExpense) => {
    setEditRecurring(item);
    setName(item.expense_name);
    setCategory(item.category);
    setAmount(Math.round(item.amount_paise / 100).toString());
    setDate(item.effective_start_month);
  };
  const openOther = (item: OtherExpense) => {
    setEditOther(item);
    setDate(item.expense_date);
    setCategory(item.category);
    setDescription(item.description);
    setAmount(Math.round(item.amount_paise / 100).toString());
  };
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!online) return toast.error("You are offline");
    save.mutate();
  };
  return (
    <Page title="Entries">
      <div className="tabs" role="tablist">
        {(
          [
            ["sales", "Sales"],
            ["recurring", "Recurring expenses"],
            ["other", "Other expenses"],
          ] as const
        ).map(([value, label]) => (
          <button
            key={value}
            className={`tab ${tab === value ? "active" : ""}`}
            role="tab"
            aria-selected={tab === value}
            onClick={() => setTab(value)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>
      <form className="card form" onSubmit={submit}>
        <h2>
          {tab === "sales"
            ? "Record daily sales"
            : tab === "recurring"
              ? "Add recurring expense"
              : "Add other expense"}
        </h2>
        {tab !== "recurring" && (
          <label>
            Date
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </label>
        )}
        {tab === "recurring" && (
          <>
            <label>
              Expense name
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </label>
            <label>
              Effective start month
              <input
                type="month"
                value={date.slice(0, 7)}
                onChange={(e) => setDate(`${e.target.value}-01`)}
                required
              />
            </label>
          </>
        )}
        {tab !== "sales" && (
          <label>
            Category
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              required
            />
          </label>
        )}
        {tab === "other" && (
          <label>
            Description
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </label>
        )}
        <label>
          {tab === "sales" ? "Total sales amount" : "Amount"}
          <input
            inputMode="numeric"
            placeholder="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
        </label>
        {save.error && (
          <p className="error" role="alert">
            <AlertCircle size={16} />
            {(save.error as Error).message}
          </p>
        )}
        <BusyButton
          className="primary"
          type="submit"
          busy={save.isPending}
          disabled={!online}
        >
          Save {tab === "sales" ? "sales" : "expense"}
        </BusyButton>
      </form>
      <section className="card">
        <h2>
          {tab === "sales"
            ? "Sales for selected month"
            : tab === "recurring"
              ? "Recurring expenses"
              : "Other expenses"}
        </h2>
        {tab === "sales" &&
          (salesLoading ? (
            <SkeletonBlock />
          ) : sales.length === 0 ? (
            <EmptyState text="No sales recorded for this month." />
          ) : (
            sales.map((item) => (
              <button
                className="list-row list-button"
                key={item.id}
                onClick={() => openSale(item)}
              >
                <span>{item.sale_date}</span>
                <strong>{formatINR(item.amount_paise)}</strong>
              </button>
            ))
          ))}
        {tab === "recurring" &&
          (recurringLoading ? (
            <SkeletonBlock />
          ) : recurring.length === 0 ? (
            <EmptyState text="No recurring expenses yet." />
          ) : (
            recurring.map((item) => (
              <div
                className="list-row list-button"
                role="button"
                tabIndex={0}
                key={item.id}
                onClick={() => openRecurring(item)}
                onKeyDown={(event) =>
                  event.key === "Enter" && openRecurring(item)
                }
              >
                <div>
                  <strong>{item.expense_name}</strong>
                  <small>
                    {item.category} Â·{" "}
                    {item.is_active
                      ? "Active"
                      : `Paused from ${item.paused_from_month?.slice(0, 7)}`}
                  </small>
                </div>
                <span className="row-end">
                  <strong>{formatINR(item.amount_paise)}</strong>
                  <button
                    className="icon-button"
                    type="button"
                    disabled={!online || resume.isPending}
                    aria-label={
                      item.is_active
                        ? `Pause ${item.expense_name}`
                        : `Resume ${item.expense_name}`
                    }
                    title={
                      item.is_active
                        ? "Pause recurring expense"
                        : "Resume recurring expense"
                    }
                    onClick={(event) => {
                      event.stopPropagation();
                      if (item.is_active) {
                        setPauseExpense(item);
                        setPauseFromMonth(indiaBusinessMonth());
                      } else {
                        resume.mutate(item);
                      }
                    }}
                  >
                    {item.is_active ? (
                      <Pause size={16} aria-hidden="true" />
                    ) : (
                      <Play size={16} aria-hidden="true" />
                    )}
                  </button>
                </span>
              </div>
            ))
          ))}
        {tab === "other" &&
          (otherLoading ? (
            <SkeletonBlock />
          ) : other.length === 0 ? (
            <EmptyState text="No other expenses yet." />
          ) : (
            other.map((item) => (
              <div
                className="list-row list-button"
                role="button"
                tabIndex={0}
                key={item.id}
                onClick={() => openOther(item)}
                onKeyDown={(event) => event.key === "Enter" && openOther(item)}
              >
                <div>
                  <strong>{item.description}</strong>
                  <small>
                    {item.expense_date} Â· {item.category}
                  </small>
                </div>
                <strong>{formatINR(item.amount_paise)}</strong>
              </div>
            ))
          ))}
      </section>
      {editRecurring && (
        <Modal
          title="Edit recurring expense"
        description="Changes apply from the selected month onward."
          onClose={() => setEditRecurring(null)}
        >
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              if (online) updateRecurring.mutate();
            }}
          >
            <label>
              Expense name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </label>
            <label>
              Category
              <input
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                required
              />
            </label>
            <label>
              Amount
              <input
                inputMode="numeric"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            <label>
              Effective from month
              <input
                type="month"
                value={date.slice(0, 7)}
                min={editRecurring.effective_start_month.slice(0, 7)}
                onChange={(event) => setDate(`${event.target.value}-01`)}
                required
              />
            </label>
            {updateRecurring.error && (
              <p className="error" role="alert">
                <AlertCircle size={16} />
                {(updateRecurring.error as Error).message}
              </p>
            )}
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setEditRecurring(null)}
                disabled={updateRecurring.isPending}
              >
                Cancel
              </button>
              <BusyButton
                className="primary"
                type="submit"
                busy={updateRecurring.isPending}
                disabled={!online}
              >
                Save change
              </BusyButton>
            </div>
          </form>
        </Modal>
      )}
      {editOther && (
        <Modal title="Edit other expense" onClose={() => setEditOther(null)}>
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              if (online) updateOther.mutate();
            }}
          >
            <label>
              Date
              <input
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                required
              />
            </label>
            <label>
              Category
              <input
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                required
              />
            </label>
            <label>
              Description
              <input
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                required
              />
            </label>
            <label>
              Amount
              <input
                inputMode="numeric"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            {updateOther.error && (
              <p className="error" role="alert">
                <AlertCircle size={16} />
                {(updateOther.error as Error).message}
              </p>
            )}
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setEditOther(null)}
                disabled={updateOther.isPending}
              >
                Cancel
              </button>
              <BusyButton
                className="primary"
                type="submit"
                busy={updateOther.isPending}
                disabled={!online}
              >
                Save changes
              </BusyButton>
            </div>
          </form>
        </Modal>
      )}
      {pauseExpense && (
        <Modal
          title={`Pause ${pauseExpense.expense_name}?`}
          description="Historical months stay unchanged. No recurring charge will be included from the selected month onward."
          onClose={() => setPauseExpense(null)}
        >
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              if (online) pause.mutate();
            }}
          >
            <label>
              Pause from month
              <input
                type="month"
                value={pauseFromMonth}
                min={pauseExpense.effective_start_month.slice(0, 7)}
                onChange={(event) => setPauseFromMonth(event.target.value)}
                required
              />
            </label>
            {pause.error && (
              <p className="error" role="alert">
                <AlertCircle size={16} />
                {(pause.error as Error).message}
              </p>
            )}
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setPauseExpense(null)}
                disabled={pause.isPending}
              >
                Cancel
              </button>
              <BusyButton
                className="primary"
                type="submit"
                busy={pause.isPending}
                disabled={!online}
              >
                Pause expense
              </BusyButton>
            </div>
          </form>
        </Modal>
      )}
      {edit && (
        <Modal
          title="Edit daily sales"
          description={`Sales recorded for ${edit.sale_date}.`}
          onClose={() => setEdit(null)}
        >
          <form
            className="form"
            onSubmit={(event) => {
              event.preventDefault();
              update.mutate(edit);
            }}
          >
            <label>
              Date
              <input
                type="date"
                value={edit.sale_date}
                onChange={(event) =>
                  setEdit({ ...edit, sale_date: event.target.value })
                }
                required
              />
            </label>
            <label>
              Total sales amount
              <input
                inputMode="numeric"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </label>
            <div className="dialog-actions">
              <button
                className="secondary"
                type="button"
                onClick={() => setConfirmDelete(edit)}
              >
                Delete
              </button>
              <BusyButton
                className="primary"
                type="submit"
                busy={update.isPending}
                disabled={!online}
              >
                Save changes
              </BusyButton>
            </div>
          </form>
        </Modal>
      )}
      {confirmDelete && (
        <ConfirmDialog
          title="Delete this sales record?"
          description={`${confirmDelete.sale_date} Â· ${formatINR(confirmDelete.amount_paise)}. This cannot be undone.`}
          confirmLabel="Delete sales"
          destructive
          busy={remove.isPending}
          onConfirm={() => remove.mutate(confirmDelete)}
          onClose={() => setConfirmDelete(null)}
        />
      )}
    </Page>
  );
}
