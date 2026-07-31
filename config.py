from pathlib import Path

TARGET_REVENUE = 400_000_000

BASE_DIR = Path(__file__).resolve().parent
REPORTS_FOLDER = str(BASE_DIR / "data" / "reports")
DATABASE_PATH = str(BASE_DIR / "database" / "revenue.db")

EXPECTED_COLUMNS = [
    "Bill Date",
    "Subcounty",
    "Ward",
    "Business Name",
    "AmountPaid",
    "Amount to Pay",
    "BillStatus"
]

VALID_SUBCOUNTIES = [
    "Ainabkoi",
    "Kapseret",
    "Kesses",
    "Moiben",
    "Soy",
    "Turbo"
]

SUBCOUNTY_TARGETS = {
    "Ainabkoi": 55_000_000,
    "Kapseret": 60_000_000,
    "Kesses": 50_000_000,
    "Moiben": 65_000_000,
    "Soy": 70_000_000,
    "Turbo": 100_000_000
}

FINANCIAL_YEAR_START_MONTH = 7

WARD_TO_SUBCOUNTY = {
    "Kapsoya": "Ainabkoi",
    "Kaptagat": "Ainabkoi",
    "Ainabkoi/Olare": "Ainabkoi",

    "Simat/Kapseret": "Kapseret",
    "Kipkenyo": "Kapseret",
    "Ngeria": "Kapseret",
    "Megun": "Kapseret",
    "Langas": "Kapseret",

    "Racecourse": "Kesses",
    "Cheptiret/Kipchamo": "Kesses",
    "Tulwet/Chuiyat": "Kesses",
    "Tarakwa": "Kesses",

    "Tembelio": "Moiben",
    "Sergoit": "Moiben",
    "Karuna/Meibeki": "Moiben",
    "Moiben": "Moiben",
    "Kimumu": "Moiben",

    "Moi's Bridge": "Soy",
    "Kapkures": "Soy",
    "Ziwa": "Soy",
    "Segero/Barsombe": "Soy",
    "Kipsomba": "Soy",
    "Soy": "Soy",
    "Kuinet/Kapsuswa": "Soy",

    "Ngenyilel": "Turbo",
    "Tapsagoi": "Turbo",
    "Kamagut": "Turbo",
    "Kiplombe": "Turbo",
    "Kapsaos": "Turbo",
    "Huruma": "Turbo",
}
