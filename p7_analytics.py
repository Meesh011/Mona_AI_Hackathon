"""
analytics.py
Core analytics engine for the targeting agent.
Computes: RFM, segment profiles, seasonal signals, category affinity,
optimal send-window, and campaign lift measurement.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from datetime import date, timedelta
from scipy import stats

# ── Load & prep ─────────────────────────────────────────────────────────────
def load_data(tx_path: str, cx_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    tx = pd.read_csv(tx_path, parse_dates=["date"])
    cx = pd.read_csv(cx_path)
    tx = tx.merge(cx[["customer_id","age","gender"]], on="customer_id", how="left")
    return tx, cx

# ── RFM ─────────────────────────────────────────────────────────────────────
def compute_rfm(tx: pd.DataFrame, snapshot: date | None = None) -> pd.DataFrame:
    snap = pd.Timestamp(snapshot or tx["date"].max())
    g = tx.groupby("customer_id").agg(
        last_purchase=("date","max"),
        frequency=("transaction_id","count"),
        monetary=("revenue","sum"),
    ).reset_index()
    g["recency_days"] = (snap - g["last_purchase"]).dt.days
    for col, asc in [("recency_days",True),("frequency",False),("monetary",False)]:
        label = col.split("_")[0][0].upper()
        g[f"{label}_score"] = pd.qcut(g[col], 4, labels=[4,3,2,1] if asc else [1,2,3,4]).astype(int)
    g["rfm_score"] = g["R_score"] + g["F_score"] + g["M_score"]
    g["rfm_segment"] = pd.cut(g["rfm_score"], bins=[0,5,8,12],
                               labels=["at_risk","mid_value","high_value"])
    return g

# ── Category affinity ────────────────────────────────────────────────────────
def category_affinity(tx: pd.DataFrame) -> pd.DataFrame:
    total = tx.groupby("customer_id")["revenue"].sum().rename("total_spend")
    by_line = tx.groupby(["customer_id","line"])["revenue"].sum().unstack(fill_value=0)
    by_line = by_line.div(total, axis=0).round(3)
    by_line.columns = [f"pct_{c.lower().replace('/','_').replace(' ','_')}" for c in by_line.columns]
    return by_line.reset_index()

# ── Seasonal patterns ────────────────────────────────────────────────────────
def seasonal_index(tx: pd.DataFrame) -> pd.DataFrame:
    tx = tx.copy()
    tx["month"] = tx["date"].dt.month
    monthly = tx.groupby(["line","month"])["revenue"].sum().reset_index()
    monthly["mean_rev"] = monthly.groupby("line")["revenue"].transform("mean")
    monthly["seasonal_index"] = (monthly["revenue"] / monthly["mean_rev"]).round(3)
    return monthly

# ── Optimal send-window per segment×SKU ─────────────────────────────────────
def send_windows(tx: pd.DataFrame) -> pd.DataFrame:
    tx = tx.copy()
    tx["month"]     = tx["date"].dt.month
    tx["dayofweek"] = tx["date"].dt.dayofweek  # 0=Mon
    by_seg_sku = (
        tx.groupby(["segment","sku","month","dayofweek"])["qty"]
        .sum().reset_index()
    )
    # best month per segment×sku
    best_month = (
        by_seg_sku.groupby(["segment","sku"])
        .apply(lambda d: d.loc[d["qty"].idxmax()][["month","dayofweek"]])
        .reset_index()
    )
    best_month.columns = ["segment","sku","best_month","best_dow"]
    MONTH_NAMES = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    DOW_NAMES   = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri",5:"Sat",6:"Sun"}
    best_month["best_month_name"] = best_month["best_month"].map(MONTH_NAMES)
    best_month["best_dow_name"]   = best_month["best_dow"].map(DOW_NAMES)
    sku_names = tx[["sku","product_name"]].drop_duplicates()
    best_month = best_month.merge(sku_names, on="sku", how="left")
    return best_month

# ── Campaign lift ────────────────────────────────────────────────────────────
def campaign_lift(
    tx: pd.DataFrame,
    campaign_sku: str,
    pre_start: str,  # YYYY-MM-DD
    pre_end: str,
    post_start: str,
    post_end: str,
) -> dict:
    mask_sku = tx["sku"] == campaign_sku
    def period_rev(group: str, start: str, end: str) -> float:
        m = mask_sku & (tx["campaign_group"]==group) & \
            (tx["date"] >= start) & (tx["date"] <= end)
        return tx.loc[m, "revenue"].sum()

    def period_customers(group: str, start: str, end: str) -> int:
        m = mask_sku & (tx["campaign_group"]==group) & \
            (tx["date"] >= start) & (tx["date"] <= end)
        return tx.loc[m, "customer_id"].nunique()

    t_pre  = period_rev("treatment", pre_start, pre_end)
    c_pre  = period_rev("control",   pre_start, pre_end)
    t_post = period_rev("treatment", post_start, post_end)
    c_post = period_rev("control",   post_start, post_end)

    t_pre_cx  = period_customers("treatment", pre_start, pre_end)
    t_post_cx = period_customers("treatment", post_start, post_end)
    c_pre_cx  = period_customers("control",   pre_start, pre_end)
    c_post_cx = period_customers("control",   post_start, post_end)

    # DiD lift
    did = (t_post - t_pre) - (c_post - c_pre)
    base = c_post if c_post > 0 else 1
    lift_pct = round(did / base * 100, 1)

    # t-test on per-customer spend (post period)
    t_spend = tx.loc[mask_sku & (tx["campaign_group"]=="treatment") &
                     (tx["date"]>=post_start) & (tx["date"]<=post_end)]\
                .groupby("customer_id")["revenue"].sum()
    c_spend = tx.loc[mask_sku & (tx["campaign_group"]=="control") &
                     (tx["date"]>=post_start) & (tx["date"]<=post_end)]\
                .groupby("customer_id")["revenue"].sum()
    if len(t_spend) > 1 and len(c_spend) > 1:
        tstat, pval = stats.ttest_ind(t_spend, c_spend, equal_var=False)
    else:
        tstat, pval = 0.0, 1.0

    return {
        "campaign_sku":       campaign_sku,
        "pre_period":         f"{pre_start} – {pre_end}",
        "post_period":        f"{post_start} – {post_end}",
        "treatment_pre_rev":  round(t_pre, 2),
        "treatment_post_rev": round(t_post, 2),
        "control_pre_rev":    round(c_pre, 2),
        "control_post_rev":   round(c_post, 2),
        "did_lift_eur":       round(did, 2),
        "lift_pct":           lift_pct,
        "t_stat":             round(tstat, 3),
        "p_value":            round(pval, 4),
        "significant":        pval < 0.05,
        "treatment_pre_cx":   t_pre_cx,
        "treatment_post_cx":  t_post_cx,
        "control_pre_cx":     c_pre_cx,
        "control_post_cx":    c_post_cx,
    }

# ── Full targeting signals report ────────────────────────────────────────────
def targeting_signals(tx: pd.DataFrame) -> pd.DataFrame:
    sw = send_windows(tx)
    seg_sku_rev = tx.groupby(["segment","sku","product_name"])["revenue"]\
                    .sum().reset_index().rename(columns={"revenue":"total_rev"})
    merged = sw.merge(seg_sku_rev, on=["segment","sku"], how="left")
    merged = merged.sort_values(["segment","total_rev"], ascending=[True,False])
    return merged