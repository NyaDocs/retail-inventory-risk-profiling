# =============================================================================
# Stockout & Overstock Risk Profiling — UCI Online Retail II
# Author: Rahmadhania
# Description: End-to-end inventory risk analysis using ABC segmentation
#              and sales velocity to flag stockout and overstock risk.
# =============================================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import warnings
import os

warnings.filterwarnings("ignore")

# ── Output directory ──────────────────────────────────────────────────────────
OUTPUT_DIR = "../outputs/charts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Plot style ────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "figure.dpi": 150,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.family": "DejaVu Sans",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
})

COLORS = {
    "A": "#E63946",   # high value — red
    "B": "#F4A261",   # mid value  — orange
    "C": "#2A9D8F",   # low value  — teal
    "stockout":   "#E63946",
    "overstock":  "#457B9D",
    "balanced":   "#2A9D8F",
    "watch":      "#F4A261",
}

# =============================================================================
# STEP 1 — LOAD DATA
# =============================================================================
print("=" * 60)
print("STEP 1 — Loading Data")
print("=" * 60)

# The dataset ships as two sheets (Year 2009-2010 and Year 2010-2011).
# We read both and concatenate them into one master DataFrame.
df_09 = pd.read_excel("../data/online_retail_II.xlsx", sheet_name="Year 2009-2010")
df_10 = pd.read_excel("../data/online_retail_II.xlsx", sheet_name="Year 2010-2011")

df = pd.concat([df_09, df_10], ignore_index=True)

print(f"  Raw rows  : {len(df):,}")
print(f"  Columns   : {list(df.columns)}")
print(f"  Date range: {df['InvoiceDate'].min()} → {df['InvoiceDate'].max()}")

# =============================================================================
# STEP 2 — DATA CLEANING
# =============================================================================
print("\n" + "=" * 60)
print("STEP 2 — Data Cleaning")
print("=" * 60)

raw_count = len(df)

# ── 2a. Remove cancellations ──────────────────────────────────────────────────
# Invoices starting with "C" are cancellations, not real sales.
# We exclude them because our goal is to measure actual sales velocity.
df = df[~df["Invoice"].astype(str).str.startswith("C")]
print(f"  After removing cancellations : {len(df):,} rows removed → {raw_count - len(df):,}")

# ── 2b. Remove non-product StockCodes ────────────────────────────────────────
# Codes like POST, D, M, BANK CHARGES, CRUK are service/admin charges,
# not physical inventory items — they would distort our risk profiling.
non_product_codes = ["POST", "D", "M", "BANK CHARGES", "CRUK", "DOT", "AMAZONFEE", "B", "S", "DCGSSBOY", "DCGSSGIRL"]
df = df[~df["StockCode"].astype(str).isin(non_product_codes)]
df = df[~df["StockCode"].astype(str).str.startswith("gift")]  # gift vouchers

# ── 2c. Drop rows with missing Customer ID ───────────────────────────────────
# ~25% of rows have no Customer ID. We drop them because without a customer
# we cannot reliably attribute demand at the SKU level.
before = len(df)
df = df.dropna(subset=["Customer ID"])
print(f"  After dropping null CustomerID: {before - len(df):,} rows removed → {len(df):,} remaining")

# ── 2d. Remove rows with zero or negative Quantity / Price ───────────────────
# Negative Quantity that survived cancellation removal = data entry errors.
# Zero Price = samples or internal use — not real commercial transactions.
df = df[df["Quantity"] > 0]
df = df[df["Price"] > 0]
print(f"  After removing bad Qty/Price : {len(df):,} rows remaining")

# ── 2e. Remove duplicate rows ────────────────────────────────────────────────
df = df.drop_duplicates()
print(f"  After deduplication          : {len(df):,} rows remaining")

# ── 2f. Derived columns ──────────────────────────────────────────────────────
# Revenue per line = Quantity × Price (unit price in GBP)
df["Revenue"] = df["Quantity"] * df["Price"]
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["YearMonth"] = df["InvoiceDate"].dt.to_period("M")

print(f"\n  ✓ Clean dataset: {len(df):,} rows | {df['StockCode'].nunique():,} unique SKUs")

# =============================================================================
# STEP 3 — ABC SEGMENTATION
# =============================================================================
print("\n" + "=" * 60)
print("STEP 3 — ABC Segmentation")
print("=" * 60)

# ABC analysis categorises products by their contribution to total revenue:
#   A = top 80% of cumulative revenue  → high-value SKUs
#   B = next 15%                        → mid-value SKUs
#   C = bottom 5%                       → low-value SKUs
# This is the standard inventory management framework used in retail/ops.

sku_revenue = (
    df.groupby(["StockCode", "Description"])
    .agg(
        TotalRevenue=("Revenue", "sum"),
        TotalQuantity=("Quantity", "sum"),
        TransactionCount=("Invoice", "nunique"),
    )
    .reset_index()
    .sort_values("TotalRevenue", ascending=False)
)

# Cumulative revenue percentage
sku_revenue["CumulativePct"] = (
    sku_revenue["TotalRevenue"].cumsum() / sku_revenue["TotalRevenue"].sum() * 100
)

# Assign ABC class
def assign_abc(cum_pct):
    if cum_pct <= 80:
        return "A"
    elif cum_pct <= 95:
        return "B"
    else:
        return "C"

sku_revenue["ABC_Class"] = sku_revenue["CumulativePct"].apply(assign_abc)

abc_summary = sku_revenue.groupby("ABC_Class").agg(
    SKU_Count=("StockCode", "count"),
    Total_Revenue=("TotalRevenue", "sum"),
).reset_index()
abc_summary["Revenue_Pct"] = abc_summary["Total_Revenue"] / abc_summary["Total_Revenue"].sum() * 100
abc_summary["SKU_Pct"] = abc_summary["SKU_Count"] / abc_summary["SKU_Count"].sum() * 100

print(abc_summary.to_string(index=False))

# =============================================================================
# STEP 4 — SALES VELOCITY & TRANSACTION FREQUENCY
# =============================================================================
print("\n" + "=" * 60)
print("STEP 4 — Sales Velocity & Transaction Frequency")
print("=" * 60)

# Sales velocity = average units sold per active month.
# This captures HOW FAST a product moves, not just total volume.
# A product with high velocity but low transaction count is ordered in bulk
# rarely → potential stockout if reorder is delayed.

# Active months = number of distinct YearMonth periods the SKU appeared in
sku_activity = (
    df.groupby("StockCode")["YearMonth"]
    .nunique()
    .reset_index()
    .rename(columns={"YearMonth": "ActiveMonths"})
)

sku_revenue = sku_revenue.merge(sku_activity, on="StockCode", how="left")

# Velocity = total quantity sold ÷ active months
sku_revenue["Velocity"] = sku_revenue["TotalQuantity"] / sku_revenue["ActiveMonths"]

# Frequency = transactions ÷ active months
sku_revenue["Frequency"] = sku_revenue["TransactionCount"] / sku_revenue["ActiveMonths"]

print(f"  Velocity stats (units/month):")
print(sku_revenue["Velocity"].describe().round(2).to_string())

# =============================================================================
# STEP 5 — RISK SCORING
# =============================================================================
print("\n" + "=" * 60)
print("STEP 5 — Risk Scoring")
print("=" * 60)

# Risk logic:
#   STOCKOUT RISK   → high velocity + low frequency
#                     (product sells fast but is ordered rarely → gaps likely)
#   OVERSTOCK RISK  → low velocity + high frequency
#                     (ordered often but sells slowly → capital tied up)
#   BALANCED        → high velocity + high frequency (healthy)
#   WATCH           → low velocity + low frequency   (slow movers to review)

v_median = sku_revenue["Velocity"].median()
f_median = sku_revenue["Frequency"].median()

print(f"  Velocity  median: {v_median:.2f} units/month")
print(f"  Frequency median: {f_median:.2f} transactions/month")

def assign_risk(row):
    hi_v = row["Velocity"] >= v_median
    hi_f = row["Frequency"] >= f_median
    if hi_v and not hi_f:
        return "Stockout Risk"
    elif not hi_v and hi_f:
        return "Overstock Risk"
    elif hi_v and hi_f:
        return "Balanced"
    else:
        return "Watch"

sku_revenue["RiskCategory"] = sku_revenue.apply(assign_risk, axis=1)

risk_summary = sku_revenue.groupby("RiskCategory").agg(
    SKU_Count=("StockCode", "count"),
    Avg_Revenue=("TotalRevenue", "mean"),
).reset_index().sort_values("SKU_Count", ascending=False)

print("\n  Risk category breakdown:")
print(risk_summary.to_string(index=False))

# =============================================================================
# STEP 6 — VISUALIZATIONS
# =============================================================================
print("\n" + "=" * 60)
print("STEP 6 — Generating Charts")
print("=" * 60)

# ── Chart 1: Pareto / ABC Revenue Curve ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))

x = range(len(sku_revenue))
color_map = sku_revenue["ABC_Class"].map(COLORS)

ax.bar(x, sku_revenue["TotalRevenue"], color=color_map, width=1.0, linewidth=0)
ax2 = ax.twinx()
ax2.plot(x, sku_revenue["CumulativePct"], color="#1D3557", linewidth=2, label="Cumulative %")
ax2.axhline(80, color=COLORS["A"], linestyle="--", linewidth=1, alpha=0.7)
ax2.axhline(95, color=COLORS["B"], linestyle="--", linewidth=1, alpha=0.7)
ax2.set_ylabel("Cumulative Revenue %", color="#1D3557")
ax2.set_ylim(0, 105)

patches = [
    mpatches.Patch(color=COLORS["A"], label="Class A (80% revenue)"),
    mpatches.Patch(color=COLORS["B"], label="Class B (next 15%)"),
    mpatches.Patch(color=COLORS["C"], label="Class C (bottom 5%)"),
]
ax.legend(handles=patches, loc="upper left", fontsize=9)
ax.set_title("ABC Segmentation — Revenue Pareto Curve", fontweight="bold", pad=12)
ax.set_xlabel("SKUs (sorted by revenue, high → low)")
ax.set_ylabel("Revenue (GBP)")
ax.set_xticks([])

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/01_abc_pareto_curve.png")
plt.close()
print("  ✓ Chart 1 saved: 01_abc_pareto_curve.png")

# ── Chart 2: ABC SKU Count vs Revenue Share ───────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(10, 4))

classes = ["A", "B", "C"]
sku_pcts = [abc_summary.loc[abc_summary["ABC_Class"] == c, "SKU_Pct"].values[0] for c in classes]
rev_pcts = [abc_summary.loc[abc_summary["ABC_Class"] == c, "Revenue_Pct"].values[0] for c in classes]
bar_colors = [COLORS[c] for c in classes]

axes[0].bar(classes, sku_pcts, color=bar_colors, width=0.5)
axes[0].set_title("% of SKUs by Class", fontweight="bold")
axes[0].set_ylabel("% of Total SKUs")
for i, v in enumerate(sku_pcts):
    axes[0].text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)

axes[1].bar(classes, rev_pcts, color=bar_colors, width=0.5)
axes[1].set_title("% of Revenue by Class", fontweight="bold")
axes[1].set_ylabel("% of Total Revenue")
for i, v in enumerate(rev_pcts):
    axes[1].text(i, v + 0.5, f"{v:.1f}%", ha="center", fontsize=10)

fig.suptitle("ABC Class Distribution", fontsize=14, fontweight="bold", y=1.02)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/02_abc_distribution.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 2 saved: 02_abc_distribution.png")

# ── Chart 3: Risk Matrix Scatter ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 7))

risk_color_map = {
    "Stockout Risk":  COLORS["stockout"],
    "Overstock Risk": COLORS["overstock"],
    "Balanced":       COLORS["balanced"],
    "Watch":          COLORS["watch"],
}

# Cap velocity and frequency at 99th percentile for readability
v_cap = sku_revenue["Velocity"].quantile(0.99)
f_cap = sku_revenue["Frequency"].quantile(0.99)
plot_df = sku_revenue[
    (sku_revenue["Velocity"] <= v_cap) &
    (sku_revenue["Frequency"] <= f_cap)
].copy()

for risk, group in plot_df.groupby("RiskCategory"):
    ax.scatter(
        group["Velocity"],
        group["Frequency"],
        c=risk_color_map[risk],
        label=risk,
        alpha=0.5,
        s=20,
        linewidths=0,
    )

# Quadrant dividers
ax.axvline(v_median, color="gray", linestyle="--", linewidth=1, alpha=0.6)
ax.axhline(f_median, color="gray", linestyle="--", linewidth=1, alpha=0.6)

# Quadrant labels
ax.text(v_cap * 0.95, f_median * 0.1,  "WATCH",         ha="right", color=COLORS["watch"],     fontsize=9, fontstyle="italic")
ax.text(v_cap * 0.95, f_cap   * 0.95,  "BALANCED",      ha="right", color=COLORS["balanced"],   fontsize=9, fontstyle="italic")
ax.text(v_median * 0.05, f_cap * 0.95, "OVERSTOCK RISK",ha="left",  color=COLORS["overstock"],  fontsize=9, fontstyle="italic")
ax.text(v_median * 0.05, f_median * 0.1,"WATCH",         ha="left",  color=COLORS["watch"],     fontsize=9, fontstyle="italic")

ax.set_title("Inventory Risk Matrix — Velocity vs. Transaction Frequency", fontweight="bold", pad=12)
ax.set_xlabel("Sales Velocity (units/month)")
ax.set_ylabel("Transaction Frequency (orders/month)")
ax.legend(loc="upper center", ncol=4, fontsize=9, bbox_to_anchor=(0.5, -0.08), frameon=False)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/03_risk_matrix.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 3 saved: 03_risk_matrix.png")

# ── Chart 4: Risk by ABC Class (stacked bar) ─────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))

risk_abc = (
    sku_revenue.groupby(["ABC_Class", "RiskCategory"])
    .size()
    .unstack(fill_value=0)
    .reindex(["A", "B", "C"])
)

risk_abc_pct = risk_abc.div(risk_abc.sum(axis=1), axis=0) * 100

risk_plot_colors = [risk_color_map.get(c, "#999") for c in risk_abc_pct.columns]
risk_abc_pct.plot(
    kind="bar",
    stacked=True,
    color=risk_plot_colors,
    ax=ax,
    width=0.5,
    edgecolor="white",
    linewidth=0.5,
)

ax.set_title("Risk Profile by ABC Class (% of SKUs)", fontweight="bold", pad=12)
ax.set_xlabel("ABC Class")
ax.set_ylabel("% of SKUs in Class")
ax.set_xticklabels(["A (High Value)", "B (Mid Value)", "C (Low Value)"], rotation=0)
ax.legend(loc="upper right", fontsize=9, frameon=False)
ax.set_ylim(0, 115)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/04_risk_by_abc_class.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 4 saved: 04_risk_by_abc_class.png")

# ── Chart 5: Top 15 Stockout Risk SKUs ───────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))

top_stockout = (
    sku_revenue[sku_revenue["RiskCategory"] == "Stockout Risk"]
    .sort_values("TotalRevenue", ascending=False)
    .head(15)
)

bars = ax.barh(
    top_stockout["Description"].str[:40],
    top_stockout["TotalRevenue"],
    color=COLORS["stockout"],
    alpha=0.85,
)

ax.set_title("Top 15 High-Revenue SKUs at Stockout Risk", fontweight="bold", pad=12)
ax.set_xlabel("Total Revenue (GBP)")
ax.invert_yaxis()

for bar, val in zip(bars, top_stockout["TotalRevenue"]):
    ax.text(bar.get_width() + 200, bar.get_y() + bar.get_height() / 2,
            f"£{val:,.0f}", va="center", fontsize=8)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/05_top_stockout_skus.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 5 saved: 05_top_stockout_skus.png")

# ── Chart 6: Monthly Revenue Trend ───────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 4))

monthly = (
    df.groupby("YearMonth")["Revenue"]
    .sum()
    .reset_index()
)
monthly["YearMonth_str"] = monthly["YearMonth"].astype(str)

ax.fill_between(
    range(len(monthly)),
    monthly["Revenue"],
    alpha=0.25,
    color="#1D3557",
)
ax.plot(range(len(monthly)), monthly["Revenue"], color="#1D3557", linewidth=2)

ax.set_xticks(range(len(monthly)))
ax.set_xticklabels(monthly["YearMonth_str"], rotation=45, ha="right", fontsize=8)
ax.set_title("Monthly Revenue Trend (Dec 2009 – Dec 2011)", fontweight="bold", pad=12)
ax.set_ylabel("Revenue (GBP)")

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/06_monthly_revenue_trend.png", bbox_inches="tight")
plt.close()
print("  ✓ Chart 6 saved: 06_monthly_revenue_trend.png")

# =============================================================================
# STEP 7 — EXPORT RESULTS
# =============================================================================
print("\n" + "=" * 60)
print("STEP 7 — Exporting Results")
print("=" * 60)

# Full profiled SKU table
sku_revenue.to_csv("../outputs/sku_risk_profile.csv", index=False)
print("  ✓ sku_risk_profile.csv exported")

# Stockout risk list — priority action table
stockout_list = (
    sku_revenue[sku_revenue["RiskCategory"] == "Stockout Risk"]
    [["StockCode", "Description", "ABC_Class", "TotalRevenue", "TotalQuantity",
      "TransactionCount", "ActiveMonths", "Velocity", "Frequency"]]
    .sort_values(["ABC_Class", "TotalRevenue"], ascending=[True, False])
)
stockout_list.to_csv("../outputs/stockout_priority_list.csv", index=False)
print("  ✓ stockout_priority_list.csv exported")

# Overstock risk list
overstock_list = (
    sku_revenue[sku_revenue["RiskCategory"] == "Overstock Risk"]
    [["StockCode", "Description", "ABC_Class", "TotalRevenue", "TotalQuantity",
      "TransactionCount", "ActiveMonths", "Velocity", "Frequency"]]
    .sort_values(["ABC_Class", "TotalRevenue"], ascending=[True, False])
)
overstock_list.to_csv("../outputs/overstock_priority_list.csv", index=False)
print("  ✓ overstock_priority_list.csv exported")

# =============================================================================
# STEP 8 — SUMMARY PRINT
# =============================================================================
print("\n" + "=" * 60)
print("FINAL SUMMARY")
print("=" * 60)

total_skus = len(sku_revenue)
for cat in ["Stockout Risk", "Overstock Risk", "Balanced", "Watch"]:
    count = len(sku_revenue[sku_revenue["RiskCategory"] == cat])
    pct = count / total_skus * 100
    print(f"  {cat:<18}: {count:>5} SKUs ({pct:.1f}%)")

a_stockout = len(sku_revenue[(sku_revenue["ABC_Class"] == "A") & (sku_revenue["RiskCategory"] == "Stockout Risk")])
print(f"\n  ⚠  Class-A SKUs at Stockout Risk: {a_stockout} — IMMEDIATE ACTION REQUIRED")

print("\n✓ Analysis complete. Check outputs/ for CSVs and charts.\n")
