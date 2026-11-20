import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../lib/api";
import { formatINR, formatPercentage, formatCompactINR } from "../lib/currency-display";
import { indiaBusinessMonth } from "../lib/business-date";

type TrendPoint = { month: string; sales_paise: number; gross_profit_paise: number; net_operating_profit_paise: number };
type AgeingBucket = { bucket: string; item_count: number; value_paise: number };
type DashboardData = { month: string; sales_paise: number; purchases_paise: number; cogs_paise: number; gross_profit_paise: number; gross_margin_percentage: number | null; recurring_expenses_paise: number; other_expenses_paise: number; net_operating_profit_paise: number; operating_margin_percentage: number | null; closing_inventory_paise: number; unsold_item_count: number; provisional: boolean; trend?: TrendPoint[]; expense_breakdown?: { category: string; amount_paise: number }[]; ageing_buckets?: AgeingBucket[]; reconciliation?: { opening_inventory_paise: number | null; purchases_paise: number; cogs_paise: number; closing_inventory_paise: number; difference_paise: number | null; warning: boolean } };

const ageingOrder = [["0_30", "0–30 days"], ["31_60", "31–60 days"], ["61_90", "61–90 days"], ["90_plus", "90+ days"]] as const;

function monthLabel(month: string) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Intl.DateTimeFormat("en-IN", { month: "short", year: "numeric" }).format(new Date(year, monthNumber - 1, 1));
}

function shortMonthLabel(month: string, index: number) {
  if (index % 2 !== 0) return "";
  const [year, monthNumber] = month.split("-").map(Number);
  return new Intl.DateTimeFormat("en-IN", { month: "short" }).format(new Date(year, monthNumber - 1, 1));
}

function PnlTable({ data, month }: { data: DashboardData; month: string }) {
  const rows: [string, number | null][] = [["Sales revenue", data.sales_paise], ["Less: COGS", data.cogs_paise], ["Gross profit", data.gross_profit_paise], ["Gross margin", data.gross_margin_percentage], ["Recurring expenses", data.recurring_expenses_paise], ["Other expenses", data.other_expenses_paise], ["Net operating profit", data.net_operating_profit_paise], ["Operating margin", data.operating_margin_percentage]];
  return <section className="card" aria-labelledby="monthly-pnl-title"><div className="section-heading"><div><h2 id="monthly-pnl-title">Monthly P&amp;L</h2><p className="muted">{month}{data.provisional ? " · Current month is provisional" : ""}</p></div></div>{rows.map(([label, value]) => <div className="pnl-row" key={label}><span>{label}</span><strong>{label.includes("margin") ? formatPercentage(value) : formatINR(value)}</strong></div>)}</section>;
}

function TrendChart({ trend }: { trend: TrendPoint[] }) {
  return <section className="card trend-card" aria-labelledby="trend-title"><div className="section-heading"><div><h2 id="trend-title">12-month P&amp;L</h2><p className="muted">Net operating profit</p></div></div><div className="trend-chart" role="img" aria-label="12-month net operating profit bar chart"><ResponsiveContainer width="100%" height={176}><BarChart data={trend} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}><CartesianGrid vertical={false} stroke="var(--border)" strokeDasharray="3 3" /><XAxis dataKey="month" tickFormatter={shortMonthLabel} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "var(--muted)" }} interval={0} /><YAxis width={52} tickFormatter={value => formatCompactINR(Number(value))} tickLine={false} axisLine={false} tick={{ fontSize: 10, fill: "var(--muted)" }} /><Tooltip formatter={value => formatINR(Number(value))} labelFormatter={label => monthLabel(String(label))} /><ReferenceLine y={0} stroke="var(--muted)" /><Bar dataKey="net_operating_profit_paise" name="Net operating profit" radius={[3, 3, 0, 0]}>{trend.map(item => <Cell key={item.month} fill={item.net_operating_profit_paise < 0 ? "var(--financial-negative)" : item.net_operating_profit_paise > 0 ? "var(--financial-positive)" : "var(--muted)"} />)}</Bar></BarChart></ResponsiveContainer></div><div className="sr-only">{trend.map(item => <span key={item.month}>{monthLabel(item.month)}: {formatINR(item.net_operating_profit_paise)}. </span>)}</div></section>;
}

export function DashboardPage() {
  const [month, setMonth] = useState(indiaBusinessMonth);
  const [details, setDetails] = useState(false);
  const query = useQuery({ queryKey: ["dashboard", month], queryFn: () => api<DashboardData>(`/api/v1/reports/dashboard?month=${month}`) });
  const header = <div className="page-heading dashboard-heading"><h1>Dashboard</h1><label className="dashboard-month-selector"><span className="sr-only">View month</span><input type="month" value={month} aria-label="View month" onChange={event => setMonth(event.target.value)} /></label></div>;
  if (query.isLoading) return <>{header}<section className="skeleton-stack" aria-label="Loading dashboard"><span className="skeleton" /><span className="skeleton" /><span className="skeleton" /></section></>;
  if (query.error) return <>{header}<section className="error-panel" role="alert">Could not load dashboard. <button className="secondary" onClick={() => query.refetch()}>Retry</button></section></>;
  const data = query.data!;
  const ageing = ageingOrder.map(([key, label]) => ({ key, label, value: data.ageing_buckets?.find(item => item.bucket === key)?.value_paise ?? 0 }));
  const maxAgeing = Math.max(...ageing.map(item => item.value), 0);
  const trend = data.trend ?? [];
  return <>
    {header}
    <div className="grid kpis">{[["Sales", data.sales_paise], ["Operating profit", data.net_operating_profit_paise]].map(([label, value]) => <section className="card kpi" key={label}><span className="muted">{label}</span><strong>{formatCompactINR(value as number)}</strong></section>)}</div>
    <section className="card ageing-card" aria-labelledby="inventory-ageing-title"><div className="section-heading"><h2 id="inventory-ageing-title">Inventory ageing</h2></div><div className="ageing-strip">{ageing.map(item => <div className="ageing-cell" key={item.key} aria-label={`${item.label}: ${formatINR(item.value)}`}><span className="ageing-label">{item.label}</span><strong>{formatCompactINR(item.value)}</strong><span className="ageing-bar-track" aria-hidden="true"><span className="ageing-bar" style={{ width: maxAgeing ? `${Math.max((item.value / maxAgeing) * 100, item.value ? 4 : 0)}%` : "0%" }} /></span></div>)}</div></section>
    <TrendChart trend={trend} />
    <button className="secondary details-toggle" aria-expanded={details} onClick={() => setDetails(value => !value)}>{details ? "Hide detailed reports" : "Show detailed reports"}</button>
    {details && <div className="dashboard-details"><PnlTable data={data} month={month} /><section className="card"><h2>Expense breakdown</h2>{data.expense_breakdown?.length ? data.expense_breakdown.map(item => <div className="list-row" key={item.category}><span>{item.category}</span><strong>{formatINR(item.amount_paise)}</strong></div>) : <p className="muted">No expenses recorded.</p>}</section><section className={`card ${data.reconciliation?.warning ? "warning-card" : ""}`}><h2>Reconciliation</h2><p className="muted">Opening + purchases − COGS should equal closing inventory.</p><div className="pnl-row"><span>Difference</span><strong>{formatINR(data.reconciliation?.difference_paise)}</strong></div></section></div>}
  </>;
}
