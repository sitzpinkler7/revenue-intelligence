import pandas as pd
import numpy as np
from datetime import datetime

from config import TARGET_REVENUE, SUBCOUNTY_TARGETS


# --------------------------------------------------
# FINANCIAL YEAR & QUARTERS
# --------------------------------------------------

def add_financial_year(df):
    df = df.copy()

    def fy(date):
        return f"{date.year}/{date.year+1}" if date.month >= 7 else f"{date.year-1}/{date.year}"

    df["FinancialYear"] = df["Bill Date"].apply(fy)
    return df


def calculate_quarter(date):
    month = date.month
    if month in [7, 8, 9]:
        return "Q1"
    elif month in [10, 11, 12]:
        return "Q2"
    elif month in [1, 2, 3]:
        return "Q3"
    return "Q4"


def add_quarter_column(df):
    df = df.copy()
    df["Quarter"] = df["Bill Date"].apply(calculate_quarter)
    return df


def current_quarter():
    month = datetime.now().month
    return calculate_quarter(datetime(datetime.now().year, month, 1))


# --------------------------------------------------
# CURRENT PERIOD
# --------------------------------------------------

def current_financial_year(df):
    df = add_financial_year(df)
    return df["FinancialYear"].max()


def current_period_data(df):
    df = add_financial_year(df)
    fy = df["FinancialYear"].max()
    return df[df["FinancialYear"] == fy]


def current_quarter_data(df):
    df = add_quarter_column(df)
    q = current_quarter()
    return df[df["Quarter"] == q]


def current_reporting_period(df):
    df = add_financial_year(df)
    df = add_quarter_column(df)

    fy = df["FinancialYear"].max()
    q = df[df["FinancialYear"] == fy]["Quarter"].max()
    latest_date = df[df["FinancialYear"] == fy]["Bill Date"].max()

    return f"{q} FY {fy} as at {latest_date.strftime('%d %B %Y')}"


def filter_by_fy(df, fy):
    df = add_financial_year(df)
    return df[df["FinancialYear"] == fy]


def get_financial_years(df):
    df = add_financial_year(df)
    return sorted(df["FinancialYear"].unique(), reverse=True)


# --------------------------------------------------
# KPI FUNCTIONS
# --------------------------------------------------

def county_kpis(df):
    total = df["AmountPaid"].sum()
    progress = (total / TARGET_REVENUE) * 100 if TARGET_REVENUE else 0
    remaining = TARGET_REVENUE - total

    return {
        "total_collected": total,
        "progress_percent": progress,
        "remaining_revenue": remaining,
        "target": TARGET_REVENUE
    }


def billing_summary(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    paid = df[df["BillStatus"] == "paid"]["AmountPaid"].sum()
    unpaid = df[df["BillStatus"] == "unpaid"]["Amount to Pay"].sum()
    partpaid = df[df["BillStatus"] == "partpayment"]["AmountPaid"].sum()
    partpaid_remaining = df[df["BillStatus"] == "partpayment"]["Amount to Pay"].sum() - partpaid
    voided = df[df["BillStatus"] == "voided"]["Amount to Pay"].sum()
    cancelled = df[df["BillStatus"] == "cancelled"]["Amount to Pay"].sum()
    total = df["Amount to Pay"].sum()

    return {
        "paid": paid,
        "unpaid": unpaid,
        "partpaid": partpaid,
        "partpaid_remaining": max(partpaid_remaining, 0),
        "voided": voided,
        "cancelled": cancelled,
        "total_billed": total,
    }


def collection_efficiency(df):
    billing = billing_summary(df)
    return (billing["paid"] / billing["total_billed"] * 100) if billing["total_billed"] else 0


def bill_status_breakdown(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()
    counts = df["BillStatus"].value_counts().reset_index()
    counts.columns = ["Status", "Count"]
    amounts = df.groupby("BillStatus")["Amount to Pay"].sum().reset_index()
    amounts.columns = ["Status", "Amount"]
    return counts.merge(amounts, on="Status")


# --------------------------------------------------
# PERFORMANCE
# --------------------------------------------------

def subcounty_performance(df):
    actuals = df.groupby("Subcounty")["AmountPaid"].sum().reset_index()
    targets = pd.DataFrame(list(SUBCOUNTY_TARGETS.items()), columns=["Subcounty", "TargetRevenue"])

    merged = actuals.merge(targets, on="Subcounty", how="left")

    merged["PerformancePercent"] = (merged["AmountPaid"] / merged["TargetRevenue"]) * 100
    merged["RevenueGap"] = merged["TargetRevenue"] - merged["AmountPaid"]

    return merged.sort_values("AmountPaid", ascending=False)


def subcounty_efficiency(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    result = df.groupby("Subcounty").agg(
        total_billed=("Amount to Pay", "sum"),
        total_paid=("AmountPaid", "sum"),
        total_bills=("BillStatus", "count"),
        paid_bills=("BillStatus", lambda x: (x == "paid").sum()),
    ).reset_index()

    result["efficiency"] = (result["total_paid"] / result["total_billed"] * 100).round(1)
    result["compliance_rate"] = (result["paid_bills"] / result["total_bills"] * 100).round(1)

    return result.sort_values("efficiency", ascending=False)


def ward_performance(df):
    return (
        df.groupby(["Subcounty", "Ward"])["AmountPaid"]
        .sum()
        .reset_index()
        .sort_values(by="AmountPaid", ascending=False)
    )


def ward_compliance(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    result = df.groupby(["Subcounty", "Ward"]).agg(
        total_bills=("BillStatus", "count"),
        paid_bills=("BillStatus", lambda x: (x == "paid").sum()),
        total_billed=("Amount to Pay", "sum"),
        total_collected=("AmountPaid", "sum"),
    ).reset_index()

    result["compliance_rate"] = (result["paid_bills"] / result["total_bills"] * 100).round(1)
    result["collection_rate"] = (result["total_collected"] / result["total_billed"] * 100).round(1)

    return result.sort_values("compliance_rate", ascending=False)


# --------------------------------------------------
# TRENDS
# --------------------------------------------------

def revenue_by_date(df):
    return (
        df.groupby("Bill Date")["AmountPaid"]
        .sum()
        .reset_index()
        .rename(columns={"AmountPaid": "Revenue"})
        .sort_values("Bill Date")
    )


def monthly_revenue_trend(df):
    df = df.copy()
    df["Month"] = df["Bill Date"].dt.to_period("M").dt.to_timestamp()

    monthly = df.groupby("Month").agg(
        revenue=("AmountPaid", "sum"),
        bills_issued=("BillStatus", "count"),
    ).reset_index()

    monthly["cumulative"] = monthly["revenue"].cumsum()

    return monthly.sort_values("Month")


def monthly_target_pace(df):
    df = add_financial_year(df)
    fy = df["FinancialYear"].max()
    fy_data = df[df["FinancialYear"] == fy].copy()

    fy_data["Month"] = fy_data["Bill Date"].dt.to_period("M").dt.to_timestamp()
    monthly = fy_data.groupby("Month")["AmountPaid"].sum().reset_index()
    monthly = monthly.sort_values("Month")
    monthly["cumulative"] = monthly["AmountPaid"].cumsum()
    monthly["target_pace"] = [TARGET_REVENUE / 12 * (i + 1) for i in range(len(monthly))]

    return monthly


# --------------------------------------------------
# COMPARISON
# --------------------------------------------------

def historical_comparison(df):
    df = add_financial_year(df)
    fy_list = sorted(df["FinancialYear"].unique())

    if len(fy_list) < 2:
        return {"current_revenue": df["AmountPaid"].sum(), "previous_revenue": 0, "growth": 0}

    current = df[df["FinancialYear"] == fy_list[-1]]["AmountPaid"].sum()
    previous = df[df["FinancialYear"] == fy_list[-2]]["AmountPaid"].sum()
    growth = ((current - previous) / previous * 100) if previous else 0

    return {"current_revenue": current, "previous_revenue": previous, "growth": growth}


def quarter_comparison(df):
    df = add_financial_year(df)
    df = add_quarter_column(df)

    current_fy = df["FinancialYear"].max()
    current_q = df[df["FinancialYear"] == current_fy]["Quarter"].max()

    return (
        df[df["Quarter"] == current_q]
        .groupby("FinancialYear")["AmountPaid"]
        .sum()
        .reset_index()
    )


def quarter_target():
    return TARGET_REVENUE / 4


def subcounty_quarter_comparison(df):
    df = add_financial_year(df)
    df = add_quarter_column(df)

    current_fy = df["FinancialYear"].max()
    current_q = df[df["FinancialYear"] == current_fy]["Quarter"].max()

    filtered = df[df["Quarter"] == current_q]
    pivot = (
        filtered.groupby(["Subcounty", "FinancialYear"])["AmountPaid"]
        .sum()
        .reset_index()
    )
    pivot = pivot.pivot(index="Subcounty", columns="FinancialYear", values="AmountPaid").fillna(0)

    fy_cols = sorted(pivot.columns)
    if len(fy_cols) >= 2:
        pivot["Growth%"] = ((pivot[fy_cols[-1]] - pivot[fy_cols[-2]]) / pivot[fy_cols[-2]]).replace([np.inf, -np.inf], 0) * 100
    else:
        pivot["Growth%"] = 0.0

    return pivot.reset_index()


def ward_quarter_comparison(df):
    df = add_financial_year(df)
    df = add_quarter_column(df)

    current_fy = df["FinancialYear"].max()
    current_q = df[df["FinancialYear"] == current_fy]["Quarter"].max()

    filtered = df[df["Quarter"] == current_q]
    pivot = (
        filtered.groupby(["Ward", "FinancialYear"])["AmountPaid"]
        .sum()
        .reset_index()
    )
    pivot = pivot.pivot(index="Ward", columns="FinancialYear", values="AmountPaid").fillna(0)

    fy_cols = sorted(pivot.columns)
    if len(fy_cols) >= 2:
        pivot["Growth%"] = ((pivot[fy_cols[-1]] - pivot[fy_cols[-2]]) / pivot[fy_cols[-2]]).replace([np.inf, -np.inf], 0) * 100
    else:
        pivot["Growth%"] = 0.0

    return pivot.reset_index()


# --------------------------------------------------
# SECTOR / ACTIVITY ANALYSIS
# --------------------------------------------------

def revenue_by_activity(df, top_n=15):
    if "activity_description" not in df.columns:
        return pd.DataFrame()

    result = df.groupby("activity_description").agg(
        total_revenue=("AmountPaid", "sum"),
        total_billed=("Amount to Pay", "sum"),
        business_count=("Business Name", "nunique"),
        bill_count=("BillStatus", "count"),
    ).reset_index()

    result["avg_revenue"] = (result["total_revenue"] / result["business_count"]).round(0)
    result = result.sort_values("total_revenue", ascending=False)

    return result.head(top_n)


def sector_concentration(df, top_n=10):
    if "activity_description" not in df.columns:
        return pd.DataFrame()

    total = df["AmountPaid"].sum()
    by_sector = df.groupby("activity_description")["AmountPaid"].sum().reset_index()
    by_sector.columns = ["Sector", "Revenue"]
    by_sector["Share%"] = (by_sector["Revenue"] / total * 100).round(1)
    by_sector = by_sector.sort_values("Revenue", ascending=False)

    return by_sector.head(top_n)


# --------------------------------------------------
# LEAKAGE
# --------------------------------------------------

def revenue_leakage(df):
    df = add_financial_year(df)

    fy_list = sorted(df["FinancialYear"].unique())
    if len(fy_list) < 2:
        return None

    prev_fy, curr_fy = fy_list[-2], fy_list[-1]

    prev = (
        df[df["FinancialYear"] == prev_fy]
        .groupby(["Business Name", "Ward", "Subcounty"])["AmountPaid"]
        .sum()
        .reset_index()
        .rename(columns={"AmountPaid": "PreviousRevenue"})
    )

    curr_businesses = df[df["FinancialYear"] == curr_fy]["Business Name"].unique()

    leakage = prev[~prev["Business Name"].isin(curr_businesses)].copy()
    leakage["LastActiveFY"] = prev_fy

    if "Owner" in df.columns:
        owners = df[["Business Name", "Owner", "Phone Number"]].drop_duplicates(subset=["Business Name"])
        leakage = leakage.merge(owners, on="Business Name", how="left")

    total = leakage["PreviousRevenue"].sum()

    return leakage.sort_values("PreviousRevenue", ascending=False), total


def leakage_by_subcounty(df):
    result = revenue_leakage(df)
    if result is None:
        return pd.DataFrame()

    leakage_df, _ = result
    return leakage_df.groupby("Subcounty").agg(
        businesses_lost=("Business Name", "count"),
        revenue_lost=("PreviousRevenue", "sum"),
    ).reset_index().sort_values("revenue_lost", ascending=False)


# --------------------------------------------------
# COLLECTIONS & COMPLIANCE
# --------------------------------------------------

def unpaid_bills_register(df, subcounty=None, ward=None):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    unpaid = df[df["BillStatus"].isin(["unpaid", "partpayment"])].copy()

    if subcounty:
        unpaid = unpaid[unpaid["Subcounty"] == subcounty]
    if ward:
        unpaid = unpaid[unpaid["Ward"] == ward]

    cols = ["Business Name", "Subcounty", "Ward", "Amount to Pay", "AmountPaid", "BillStatus", "Bill Date"]
    if "Owner" in unpaid.columns:
        cols.append("Owner")
    if "Phone Number" in unpaid.columns:
        cols.append("Phone Number")
    if "activity_description" in unpaid.columns:
        cols.append("activity_description")

    available_cols = [c for c in cols if c in unpaid.columns]
    unpaid = unpaid[available_cols].copy()
    unpaid["Outstanding"] = unpaid["Amount to Pay"] - unpaid["AmountPaid"]

    return unpaid.sort_values("Outstanding", ascending=False)


def aging_analysis(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    unpaid = df[df["BillStatus"].isin(["unpaid", "partpayment"])].copy()
    today = pd.Timestamp.now()
    unpaid["days_outstanding"] = (today - unpaid["Bill Date"]).dt.days

    def age_bucket(days):
        if days <= 30:
            return "0-30 days"
        elif days <= 90:
            return "31-90 days"
        elif days <= 180:
            return "91-180 days"
        elif days <= 365:
            return "181-365 days"
        return "Over 1 year"

    unpaid["aging_bucket"] = unpaid["days_outstanding"].apply(age_bucket)

    result = unpaid.groupby("aging_bucket").agg(
        count=("BillStatus", "count"),
        total_outstanding=("Amount to Pay", "sum"),
    ).reset_index()

    bucket_order = ["0-30 days", "31-90 days", "91-180 days", "181-365 days", "Over 1 year"]
    result["aging_bucket"] = pd.Categorical(result["aging_bucket"], categories=bucket_order, ordered=True)
    return result.sort_values("aging_bucket")


def voided_cancelled_analysis(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    vc = df[df["BillStatus"].isin(["voided", "cancelled"])].copy()

    by_status = vc.groupby("BillStatus").agg(
        count=("BillStatus", "count"),
        total_amount=("Amount to Pay", "sum"),
    ).reset_index()

    by_subcounty = vc.groupby(["Subcounty", "BillStatus"]).agg(
        count=("BillStatus", "count"),
        total_amount=("Amount to Pay", "sum"),
    ).reset_index()

    return by_status, by_subcounty


def partpayment_tracking(df):
    df = df.copy()
    df["BillStatus"] = df["BillStatus"].astype(str).str.lower().str.strip()

    pp = df[df["BillStatus"] == "partpayment"].copy()
    pp["outstanding"] = pp["Amount to Pay"] - pp["AmountPaid"]
    pp["payment_percent"] = (pp["AmountPaid"] / pp["Amount to Pay"] * 100).round(1)

    cols = ["Business Name", "Subcounty", "Ward", "Amount to Pay", "AmountPaid", "outstanding", "payment_percent"]
    if "Owner" in pp.columns:
        cols.append("Owner")
    if "Phone Number" in pp.columns:
        cols.append("Phone Number")

    available_cols = [c for c in cols if c in pp.columns]
    return pp[available_cols].sort_values("outstanding", ascending=False)
