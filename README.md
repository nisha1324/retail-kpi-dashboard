# Retail KPI dashboard (Streamlit)

> 🚧 **In progress.** The data prep, the tested KPI layer and the first dashboard page are done. More views are coming (see the roadmap).

An interactive KPI dashboard for a UK online gift wholesaler. It answers the questions a commercial manager asks every month: *Are we growing? Is it more orders or bigger orders? Are returns getting worse?* Every number is compared with the same period last year.

## Data
**UCI Online Retail II**: 1,067,371 invoice lines from a UK-based online retailer, Dec 2009 to Dec 2011.
Chen, D. (2019). *Online Retail II*. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. Licensed **CC BY 4.0**.
The raw file (~46 MB) is not committed; `scripts/download_data.py` fetches it.

## Data prep (`scripts/prepare_data.py`)
| Rule | Rows removed |
|---|---:|
| The two sheets overlap on 2010-12-01..09 (identical rows) | 22,523 |
| Exact duplicate rows | 11,812 |
| Non-product stock codes (postage, fees, adjustments) | 5,980 |
| Price ≤ 0 | 5,928 |

That leaves **1,021,128 clean lines**. Cancellations (17,914 lines) are kept as negative returns, so revenue can be shown net of returns. Full log: [`results/prep_log.md`](results/prep_log.md).

## KPI definitions (`app/kpis.py`, unit-tested)
| KPI | Definition |
|---|---|
| Net revenue | Gross sales − returns |
| Orders | Distinct sale invoices |
| Avg order value (AOV) | Gross sales ÷ orders |
| Active customers | Distinct identified customers with a sale |
| Return rate | Returns ÷ gross sales |

## First look: Jan–Nov 2011 vs Jan–Nov 2010 (the dashboard's default view)
| KPI | 2011 | vs 2010 |
|---|---:|---:|
| Net revenue | £8,572,499 | +2.3% |
| Orders | 17,407 | −3.7% |
| Avg order value | £509 | +7.0% |
| Active customers | 4,168 | +1.0% |
| Return rate | 3.2% | up from 2.6% |

![Monthly net revenue, 2011 vs 2010](docs/monthly_net_revenue_2011_vs_2010.png)

**So what?** Growth came from **bigger baskets, not more orders**: orders fell 3.7% while AOV rose 7.0%. The customer base was almost flat (+1.0%), so the business relies on existing accounts spending more. Returns grew faster than sales (3.2% of gross vs 2.6%), which takes back part of the gain and is worth investigating. September was the stand-out month (~£1.0M vs ~£0.84M a year earlier); April was the weak spot.

## How to run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_data.py      # ~46 MB
python scripts/prepare_data.py       # ~1.5 min, writes data/processed/transactions.parquet
pytest                               # KPI unit tests + app smoke test
streamlit run app/dashboard.py
```
Use the filters to change the period and the country. YoY deltas are hidden when no data exists for the same period last year.

## Roadmap
- [x] Data prep + KPI layer + overview page (KPI tiles, monthly trend vs last year)
- [ ] Product and country breakdowns (what drove the AOV rise and the returns increase)
- [ ] Customer view (new vs returning, retention)
- [ ] Deployment notes for Streamlit Community Cloud, plus findings and recommendations
