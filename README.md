# 📦 Stockout & Overstock Risk Profiling

## 📌 Overview
An end-to-end inventory risk analysis of a UK-based online retailer using the UCI Online Retail II dataset. This project identifies which products are at risk of stocking out and which are tying up capital through overstocking, using ABC segmentation and sales velocity metrics.

## ❓ Business Question
> **Which products show high sales velocity but low transaction frequency (stockout risk), and which show the opposite — low velocity but high frequency (overstock risk)?**

Inventory imbalance is a silent profit killer. Stockouts lose sales and damage customer trust; overstock ties up working capital and drives up storage costs. This analysis gives operations and procurement teams a clear, data-driven view of where to act first.

## 🗂️ Dataset
- **Source:** [UCI Online Retail II via Kaggle](https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci)
- **Period:** December 2009 – December 2011
- **Size:** ~1,000,000 rows × 8 columns (before cleaning)
- **Key columns:**

| Column | Description |
|---|---|
| `Invoice` | Invoice number — prefix "C" = cancellation |
| `StockCode` | Product/SKU identifier |
| `Description` | Product name |
| `Quantity` | Units per transaction (negative = return) |
| `InvoiceDate` | Date and time of transaction |
| `Price` | Unit price in GBP |
| `Customer ID` | Unique customer identifier |
| `Country` | Customer's country |

## 🔧 Methodology

```
Load Data → Data Cleaning → ABC Segmentation → Velocity & Frequency Metrics → Risk Scoring → Visualization → Recommendation
```

1. **Data Cleaning** — Removed cancellations (Invoice prefix "C"), non-product StockCodes (POST, bank charges, etc.), null Customer IDs, and rows with zero/negative Quantity or Price.
2. **ABC Segmentation** — Classified SKUs by cumulative revenue contribution: Class A (top 80%), Class B (next 15%), Class C (bottom 5%).
3. **Sales Velocity** — Calculated average units sold per active month per SKU.
4. **Transaction Frequency** — Calculated average number of orders per active month per SKU.
5. **Risk Scoring** — Placed each SKU into one of four quadrants (Stockout Risk, Overstock Risk, Balanced, Watch) based on whether velocity and frequency are above or below the median.

## 📊 Key Findings

- **Class A SKUs are a minority of the catalogue but drive 80% of total revenue** — mismanaging even a few of them has an outsized impact on the business.
- **Stockout Risk SKUs show high velocity but low order frequency** — these products sell fast but are replenished infrequently, creating gaps in availability.
- **Overstock Risk SKUs are frequently ordered but slow-moving** — procurement is ordering these too often, unnecessarily tying up working capital.
- **A consistent revenue spike appears in November** — seasonal demand needs to be anticipated with forward stocking, especially for Class-A Stockout-Risk products.
- **"Watch" SKUs (low velocity + low frequency) are candidates for catalogue review** — some may be dead stock that should be discontinued to reduce storage costs.

## 💡 Recommendations

| Priority | Action | Target SKUs |
|---|---|---|
| 🔴 Immediate | Review reorder points, set safety stock | Class-A Stockout Risk |
| 🔵 Short-term | Reduce order frequency or batch size | Overstock Risk |
| 🟡 Medium-term | Evaluate for discontinuation | Watch (especially Class-C) |
| 🟢 Ongoing | Maintain current replenishment cycle | Balanced |

## 🛠️ Tools Used
Python · Pandas · NumPy · Matplotlib · Seaborn

## 📁 Repository Structure

```
retail-inventory-risk-profiling/
│
├── data/
│   └── online_retail_II.xlsx          # Raw dataset (download from Kaggle)
│
├── notebooks/
│   └── stockout_overstock_risk_profiling.ipynb   # Full analysis with narrative
│
├── scripts/
│   └── analysis.py                    # Clean, reusable Python script
│
├── outputs/
│   ├── sku_risk_profile.csv           # Full SKU table with risk scores
│   ├── stockout_priority_list.csv     # Stockout-risk SKUs sorted by priority
│   ├── overstock_priority_list.csv    # Overstock-risk SKUs sorted by priority
│   └── charts/
│       ├── 01_abc_pareto_curve.png
│       ├── 02_abc_distribution.png
│       ├── 03_risk_matrix.png
│       ├── 04_risk_by_abc_class.png
│       ├── 05_top_stockout_skus.png
│       └── 06_monthly_revenue_trend.png
│
├── setup_repo.py                      # Auto-creates folder structure locally
├── requirements.txt                   # Python dependencies
└── README.md
```

## ▶️ How to Run

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/retail-inventory-risk-profiling.git
cd retail-inventory-risk-profiling
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Download the dataset
- Go to [Kaggle — UCI Online Retail II](https://www.kaggle.com/datasets/mashlyn/online-retail-ii-uci)
- Download `online_retail_II.xlsx`
- Place it in the `data/` folder

### 4a. Run via Jupyter Notebook (recommended for storytelling)
```bash
jupyter notebook notebooks/stockout_overstock_risk_profiling.ipynb
```

### 4b. Run via Python script (recommended for reuse)
```bash
cd scripts
python analysis.py
```

### 5. View outputs
- Charts → `outputs/charts/`
- Risk tables → `outputs/*.csv`

---

*Dataset: UCI Online Retail II · Analysis by Rahmadhania · 2024*
