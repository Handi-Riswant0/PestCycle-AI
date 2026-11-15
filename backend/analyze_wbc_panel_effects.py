
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import rankdata

# ============================================================
# PESTCYCLE AI
# ANALISIS PANEL CUACA DAN WBC
# KONTROL EFEK WILAYAH DAN BULAN
# ============================================================

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

INPUT = DATA / "nasa_wbc_monthly_integrated_2026.csv"

OUTPUT = DATA / "wbc_panel_effects_2026.csv"
OUTPUT_MONTHLY = DATA / "wbc_monthly_trends_2026.csv"
OUTPUT_AUDIT = DATA / "wbc_panel_effects_audit.txt"

WEATHER = [
    "T2M_MEAN",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M_MEAN",
    "PRECTOTCORR_SUM"
]

TARGETS = [
    "WBC_AFFECTED_HA",
    "WBC_PUSO_HA"
]

print("=" * 65)
print("PESTCYCLE AI - ANALISIS PANEL WBC")
print("=" * 65)

# ------------------------------------------------------------
# 1. MEMBACA DATA
# ------------------------------------------------------------

df = pd.read_csv(INPUT)

df["YEAR"] = pd.to_numeric(df["YEAR"])
df["MONTH"] = pd.to_numeric(df["MONTH"])

df = df.sort_values(
    ["REGION_KEY", "YEAR", "MONTH"]
).reset_index(drop=True)

print("\n[1] DATASET")
print("Baris:", len(df))
print("Wilayah:", df["REGION_KEY"].nunique())
print("Bulan:", df["MONTH"].nunique())

# ------------------------------------------------------------
# 2. MEMBUAT TIME LAG
# ------------------------------------------------------------

for col in WEATHER:
    df[f"{col}_LAG1"] = (
        df.groupby("REGION_KEY")[col].shift(1)
    )

# ------------------------------------------------------------
# 3. FUNGSI KORELASI PANEL
# ------------------------------------------------------------

def two_way_demean(series, region, month):

    result = series.copy()

    # Efek tetap wilayah dan bulan
    for _ in range(20):

        result = (
            result
            - result.groupby(region).transform("mean")
            - result.groupby(month).transform("mean")
            + result.mean()
        )

    return result


def panel_correlation(data, weather, target):

    temp = data[
        ["REGION_KEY", "MONTH", weather, target]
    ].dropna().copy()

    if len(temp) < 20:
        return None

    if temp["REGION_KEY"].nunique() < 2:
        return None

    if temp["MONTH"].nunique() < 2:
        return None

    # Ranking untuk pendekatan asosiasi Spearman
    temp["X_RANK"] = rankdata(
        temp[weather].to_numpy()
    )

    temp["Y_RANK"] = rankdata(
        temp[target].to_numpy()
    )

    # Mengendalikan efek tetap wilayah dan bulan
    temp["X_WITHIN"] = two_way_demean(
        temp["X_RANK"],
        temp["REGION_KEY"],
        temp["MONTH"]
    )

    temp["Y_WITHIN"] = two_way_demean(
        temp["Y_RANK"],
        temp["REGION_KEY"],
        temp["MONTH"]
    )

    if (
        temp["X_WITHIN"].std() == 0
        or temp["Y_WITHIN"].std() == 0
    ):
        rho = np.nan
    else:
        rho = temp["X_WITHIN"].corr(
            temp["Y_WITHIN"]
        )

    return {
        "N": len(temp),
        "REGIONS": temp["REGION_KEY"].nunique(),
        "MONTHS": temp["MONTH"].nunique(),
        "CORRELATION": rho
    }


# ------------------------------------------------------------
# 4. ANALISIS BULAN YANG SAMA
# ------------------------------------------------------------

print("\n[2] ANALISIS EFEK WILAYAH DAN BULAN")

records = []

for weather in WEATHER:

    for target in TARGETS:

        result = panel_correlation(
            df, weather, target
        )

        if result is None:
            continue

        records.append({
            "ANALYSIS": "SAME_MONTH",
            "WEATHER": weather,
            "TARGET": target,
            **result
        })

# ------------------------------------------------------------
# 5. ANALISIS LAG 1 BULAN
# ------------------------------------------------------------

print("\n[3] ANALISIS TIME LAG")

lag_df = df.dropna(
    subset=[f"{col}_LAG1" for col in WEATHER]
).copy()

for weather in WEATHER:

    lag_col = f"{weather}_LAG1"

    for target in TARGETS:

        result = panel_correlation(
            lag_df, lag_col, target
        )

        if result is None:
            continue

        records.append({
            "ANALYSIS": "LAG_1_MONTH",
            "WEATHER": lag_col,
            "TARGET": target,
            **result
        })

result_df = pd.DataFrame(records)

result_df.to_csv(
    OUTPUT,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 6. TREN BULANAN
# ------------------------------------------------------------

print("\n[4] MENYUSUN TREN BULANAN")

monthly = (
    df.groupby("MONTH")
    .agg(
        TOTAL_AFFECTED=("WBC_AFFECTED_HA", "sum"),
        TOTAL_PUSO=("WBC_PUSO_HA", "sum"),
        MEAN_TEMPERATURE=("T2M_MEAN", "mean"),
        MEAN_HUMIDITY=("RH2M_MEAN", "mean"),
        MEAN_RAINFALL=("PRECTOTCORR_SUM", "mean"),
        REGIONS=("REGION_KEY", "nunique")
    )
    .reset_index()
)

monthly.to_csv(
    OUTPUT_MONTHLY,
    index=False,
    encoding="utf-8-sig"
)

# ------------------------------------------------------------
# 7. AUDIT
# ------------------------------------------------------------

audit = [
    "=" * 65,
    "AUDIT ANALISIS PANEL WBC",
    "=" * 65,
    f"Observasi: {len(df)}",
    f"Wilayah: {df['REGION_KEY'].nunique()}",
    f"Bulan: {df['MONTH'].nunique()}",
    "",
    "METODE:",
    "Ranking Spearman",
    "Two-way demeaning",
    "Kontrol efek wilayah",
    "Kontrol efek bulan",
    "",
    "CATATAN:",
    "Analisis bersifat eksploratif.",
    "Korelasi tidak membuktikan kausalitas.",
    "Tidak menggunakan p-value inferensial.",
    "Periode observasi hanya Januari-Oktober 2026.",
    "",
    "HASIL PANEL:",
    result_df.to_string(index=False),
    "",
    "FILE OUTPUT:",
    str(OUTPUT),
    str(OUTPUT_MONTHLY),
    "=" * 65
]

OUTPUT_AUDIT.write_text(
    "\n".join(audit),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 8. HASIL
# ------------------------------------------------------------

print("\n[5] HASIL KORELASI PANEL")

print(
    result_df.to_string(index=False)
)

print("\nTREN BULANAN")

print(
    monthly.to_string(index=False)
)

print("\nFILE OUTPUT:")
print(OUTPUT)
print(OUTPUT_MONTHLY)
print(OUTPUT_AUDIT)

print("\nANALISIS PANEL SELESAI")
print("=" * 65)
