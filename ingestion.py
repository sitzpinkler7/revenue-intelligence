import os
import pandas as pd

from config import (
    REPORTS_FOLDER,
    EXPECTED_COLUMNS,
    VALID_SUBCOUNTIES,
    WARD_TO_SUBCOUNTY,
)


# -----------------------------------
# LOAD FILE
# -----------------------------------

def load_file(filepath):

    if filepath.endswith(".csv"):
        df = pd.read_csv(filepath)

    elif filepath.endswith(".xlsx"):
        df = pd.read_excel(filepath)

    else:
        return None

    return df


# -----------------------------------
# VALIDATE COLUMNS
# -----------------------------------

def validate_columns(df, filename):

    df.columns = df.columns.str.strip()

    missing = [col for col in EXPECTED_COLUMNS if col not in df.columns]

    if missing:
        raise ValueError(
            f"{filename} missing required columns: {missing}"
        )


# -----------------------------------
# CLEAN / STANDARDIZE DATA
# -----------------------------------

def standardize_data(df):

    df = df.copy()

    df.columns = df.columns.str.strip()

    df["AmountPaid"] = (
        pd.to_numeric(df["AmountPaid"], errors="coerce")
        .fillna(0)
        .round(0)
        .astype(int)
    )

    df["Amount to Pay"] = (
        pd.to_numeric(df["Amount to Pay"], errors="coerce")
        .fillna(0)
        .round(0)
        .astype(int)
    )

    df["Bill Date"] = pd.to_datetime(
        df["Bill Date"], errors="coerce"
    )

    df["Subcounty"] = df["Subcounty"].astype(str).str.strip().str.title()

    df["Ward"] = (
        df["Ward"].astype(str).str.strip()
        .str.replace("‘", "'", regex=False)
        .str.replace("’", "'", regex=False)
        .str.title()
        .str.replace("'S ", "'s ", regex=False)
    )

    df["Business Name"] = df["Business Name"].astype(str).str.strip()

    df["BillStatus"] = (
        df["BillStatus"]
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # Normalize common ward name variations (applied after .str.title())
    ward_normalize = {
        "Tulwet/Chuiyat": "Tulwet/Chuiyat",
        "Tulwet/chuiyat": "Tulwet/Chuiyat",
        "Mois Bridge": "Moi's Bridge",
        "Moi'S Bridge": "Moi's Bridge",
        "Moi's Bridge": "Moi's Bridge",
        "Kunet/Kapsuswa": "Kuinet/Kapsuswa",
        "Simat/kapseret": "Simat/Kapseret",
        "Karuna/meibeki": "Karuna/Meibeki",
        "Segero/barsombe": "Segero/Barsombe",
        "Ainabkoi/olare": "Ainabkoi/Olare",
        "Cheptiret/kipchamo": "Cheptiret/Kipchamo",
    }
    df["Ward"] = df["Ward"].replace(ward_normalize)

    # Correct ward-to-subcounty misclassifications
    df["Subcounty"] = df["Ward"].map(WARD_TO_SUBCOUNTY).fillna(df["Subcounty"])

    # Remove invalid subcounties
    df = df[df["Subcounty"].isin(VALID_SUBCOUNTIES)]

    # Remove rows without bill date or with nan wards
    df = df.dropna(subset=["Bill Date"])
    df = df[df["Ward"].notna() & (df["Ward"] != "Nan") & (df["Ward"] != "")]

    return df


# -----------------------------------
# MAIN INGESTION PIPELINE
# -----------------------------------

def ingest_reports():

    all_data = []

    for filename in os.listdir(REPORTS_FOLDER):

        filepath = os.path.join(REPORTS_FOLDER, filename)

        if not os.path.isfile(filepath):
            continue

        if filename.startswith(".") or filename.startswith("~"):
            continue

        df = load_file(filepath)

        if df is None:
            continue

        validate_columns(df, filename)

        df = standardize_data(df)

        df["SourceFile"] = filename

        all_data.append(df)

    if not all_data:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

    combined = pd.concat(all_data, ignore_index=True)

    # -----------------------------------
    # STRONG DUPLICATE DETECTION
    # -----------------------------------

    combined["transaction_key"] = (
        combined["Bill Date"].astype(str)
        + combined["Business Name"].str.lower().str.strip()
        + combined["Ward"].str.lower().str.strip()
        + combined["Amount to Pay"].astype(str)
    )

    before = len(combined)

    combined = combined.drop_duplicates(
        subset=["transaction_key"]
    )

    after = len(combined)

    print(f"Duplicates removed: {before-after}")

    combined = combined.drop(columns=["transaction_key"])

    return combined
