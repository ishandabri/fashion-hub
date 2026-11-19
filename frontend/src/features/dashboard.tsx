import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { formatINR, formatPercentage, formatCompactINR } from "../lib/currency";
import { indiaBusinessMonth } from "../lib/business-date";

type DashboardData = { month: string; sales_paise: number; purchases_paise: number; cogs_paise: number; gross_profit_paise: number; gross_margin_percentage: number | null; recurring_expenses_paise: number; other_expenses_paise: number; net_operating_profit_paise: number; operating_margin_percentage: number | null; closing_inventory_paise: number; unsold_item_count: number; provisional: boolean; trend?: { month: string; sales_paise: number; gross_profit_paise: number; net_operating_profit_paise: number }[]; expense_breakdown?: { category: string; amount_paise: number }[]; ageing_buckets?: { bucket: string; item_count: number; value_paise: number }[]; reconciliation?: { opening_inventory_paise: number | null; purchases_paise: number; cogs_paise: number; closing_inventory_paise: number; difference_paise: number | null; warning: boolean } };

export function DashboardPage() {
  const [month, setMonth] = useState(indiaBusinessMonth);
  const [details, setDetails] = useState(false);
  const query = useQuery({ queryKey: ["dashboard", month], queryFn: () => api<DashboardData>(`/api/v1/reports/dashboard?month=${month}`) });
  if (query.isLoading) return <section className="skeleton-stack" aria-label="Loading dashboard"><span className="skeleton" /><span className="skeleton" /><span className="skeleton" /></section>;
  if (query.error) return <section className="error-panel" role="alert">Could not load dashboard. <button className="secondary" onClick={() => query.refetch()}>Retry</button></section>;
  const data = query.data!;
  const ageing90 = data.ageing_buckets?.find(item => item.bucket === "90_plus" && item.item_count > 0);
  const attention: string[] = [];
  if (ageing90) attention.push(`${ageing90.item_count} item(s) over 90 days old`);
  return <>
    <div className="month-selector"><label>View month<input type="month" value={month} onChange={event => setMonth(event.target.value)} /></label></div>
    {attention.length > 0 && <section className="attention-card" aria-label="Needs attention"><strong>Needs attention</strong><div>{attention.map(item => <span key={item}>{item}</span>)}</div></section>}
    <div className="grid kpis">{[['Sales', data.sales_paise], ['Operating profit', data.net_operating_profit_paise], ['Unsold items', data.unsold_item_count]].map(([label, value]) => <section className="card kpi" key={label as string}><span className="muted">{label}</span><strong>{label === "Unsold items" ? value : formatCompactINR(value as number)}</strong></section>)}</div>
    <section className="card"><div className="section-heading"><div><h2>Monthly P&amp;L</h2><p className="muted">{month}{data.provisional ? " · Current month is provisional" : ""}</p></div></div>{[['Sales revenue', data.sales_paise], ['Less: COGS', data.cogs_paise], ['Gross profit', data.gross_profit_paise], ['Gross margin', data.gross_margin_percentage], ['Recurring expenses', data.recurring_expenses_paise], ['Other expenses', data.other_expenses_paise], ['Net operating profit', data.net_operating_profit_paise], ['Operating margin', data.operating_margin_percentage]].map(([label, value]) => <div className="pnl-row" key={label as string}><span>{label}</span><strong>{String(label).includes("margin") ? formatPercentage(value as number) : formatINR(value as number)}</strong></div>)}</section>
    <button className="secondary details-toggle" aria-expanded={details} onClick={() => setDetails(value => !value)}>{details ? "Hide detailed reports" : "Show detailed reports"}</button>
    {details && <div className="dashboard-details"><section className="card"><h2>12-month trend</h2>{data.trend?.map(item => <div className="list-row" key={item.month}><span>{item.month}</span><span>{formatINR(item.sales_paise)} · NP {formatINR(item.net_operating_profit_paise)}</span></div>)}</section><section className="card"><h2>Inventory ageing</h2>{data.ageing_buckets?.map(item => <div className="list-row" key={item.bucket}><span>{item.bucket.replace("_", " ")}</span><strong>{item.item_count} · {formatINR(item.value_paise)}</strong></div>)}</section><section className="card"><h2>Expense breakdown</h2>{data.expense_breakdown?.length ? data.expense_breakdown.map(item => <div className="list-row" key={item.category}><span>{item.category}</span><strong>{formatINR(item.amount_paise)}</strong></div>) : <p className="muted">No expenses recorded.</p>}</section><section className={`card ${data.reconciliation?.warning ? "warning-card" : ""}`}><h2>Reconciliation</h2><p className="muted">Opening + purchases − COGS should equal closing inventory.</p><div className="pnl-row"><span>Difference</span><strong>{formatINR(data.reconciliation?.difference_paise)}</strong></div></section></div>}
  </>;
}
