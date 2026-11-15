import pandas as pd
import numpy as np
import joblib
from datetime import date
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"

def first_existing(*names):
    for name in names:
        path = DATA / name
        if path.exists():
            return path
    raise FileNotFoundError(f"Dataset tidak ditemukan. Dicari: {', '.join(names)}")

WEATHER_FILE = first_existing(
    "nasa_power_daily_38_regions_2020_2026.csv",
    "nasa_power_daily_38_regions.csv",
    "nasa_power_2020_2025_grid.csv",
)
WBC_FILE = first_existing("wbc_siperdittan_2026_clean.csv", "wbc_siperdittan_2026.csv")
FORECAST_FILE = first_existing("wbc_bbopt_forecast_clean.csv", "wbc_forecast_bbpt_2022_2025.csv")

weather = pd.read_csv(WEATHER_FILE, parse_dates=["DATE"])
wbc = pd.read_csv(WBC_FILE)
forecast = pd.read_csv(FORECAST_FILE)

def normalize_region(value):
    if pd.isna(value):
        return ""
    return " ".join(str(value).strip().upper().split())

if "REGION" not in wbc.columns:
    wbc["REGION"] = wbc["kabupaten_kota"].map(normalize_region)
wbc["REGION"] = wbc["REGION"].map(normalize_region)
wbc["kabupaten_kota"] = wbc["kabupaten_kota"].astype(str).str.strip()
forecast["kabupaten_kota"] = forecast["kabupaten_kota"].astype(str).str.strip()

REGIONS = sorted(wbc["kabupaten_kota"].dropna().unique().tolist(), key=str.casefold)
WEATHER_REGION_COL = "REGION" if "REGION" in weather.columns else None
if WEATHER_REGION_COL:
    weather["REGION_KEY"] = weather["REGION"].map(normalize_region)
else:
    weather["REGION_KEY"] = ""

def records(df):
    return df.astype(object).where(pd.notna(df), None).to_dict(orient="records")

def region_filter(df, region, col="REGION"):
    if region and col in df.columns:
        key = normalize_region(region)
        return df[df[col].map(normalize_region) == key]
    return df

app = FastAPI(
    title="PestCycle AI API",
    description="API dashboard pemantauan WBC dan cuaca NASA POWER Jawa Timur.",
    version="1.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=False,
    allow_methods=["*"], allow_headers=["*"]
)

@app.get("/")
def root():
    return {
        "application": "PestCycle AI", "version": "1.1.0", "status": "running",
        "docs": "/docs", "health": "/api/health"
    }

@app.get("/api/health")
def health():
    start = weather["DATE"].min()
    end = weather["DATE"].max()
    nasa_regions = int(weather["REGION_KEY"].nunique()) if WEATHER_REGION_COL else 0
    return {
        "status": "ok",
        "application": "PestCycle AI",
        "weather_rows": int(len(weather)),
        "weather_start": start.strftime("%Y-%m-%d"),
        "weather_end": end.strftime("%Y-%m-%d"),
        "weather_regions": nasa_regions,
        "wbc_2026_rows": int(len(wbc)),
        "wbc_regions": int(wbc["REGION"].nunique()),
        "bbpopt_rows": int(len(forecast)),
        "model_status": "experimental_not_production_validated",
        "datasets": {
            "nasa_power": {"file": WEATHER_FILE.name, "rows": int(len(weather)), "start": start.strftime("%Y-%m-%d"), "end": end.strftime("%Y-%m-%d"), "regions": nasa_regions},
            "siperdittan_2026": {"file": WBC_FILE.name, "rows": int(len(wbc)), "regions": int(wbc["REGION"].nunique())},
            "bbpopt": {"file": FORECAST_FILE.name, "rows": int(len(forecast))}
        },
        "notice": "Data aktual WBC tersedia Januari-Oktober 2026. Prakiraan BBPOPT ditampilkan terpisah dari observasi aktual."
    }

@app.get("/api/regions")
def get_regions():
    return {"total_regions": len(REGIONS), "regions": REGIONS}

@app.get("/api/weather/latest")
def weather_latest(region: str = ""):
    d = weather.copy()
    if region and WEATHER_REGION_COL:
        d = region_filter(d, region, "REGION_KEY")
    if d.empty:
        raise HTTPException(status_code=404, detail="Data cuaca wilayah tidak ditemukan.")
    last = d["DATE"].max()
    d = d[d["DATE"] == last]
    cols = [c for c in ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR"] if c in d.columns]
    means = d[cols].mean(numeric_only=True)
    return {
        "date": last.strftime("%Y-%m-%d"),
        "region": region or "Rata-rata 38 kabupaten/kota",
        "regions_included": int(d["REGION_KEY"].nunique()) if WEATHER_REGION_COL else None,
        "values": {k: round(float(v), 2) if pd.notna(v) else None for k, v in means.items()}
    }

@app.get("/api/weather/series")
def weather_series(
    start: str = "2020-01-01",
    end: str = "2026-10-31",
    aggregation: str = Query(default="monthly", pattern="^(daily|monthly)$"),
    region: str = ""
):
    try:
        start_date, end_date = pd.to_datetime(start), pd.to_datetime(end)
    except Exception:
        raise HTTPException(status_code=400, detail="Tanggal harus berformat YYYY-MM-DD.")
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Tanggal awal melebihi tanggal akhir.")
    d = weather[(weather["DATE"] >= start_date) & (weather["DATE"] <= end_date)].copy()
    if region and WEATHER_REGION_COL:
        d = region_filter(d, region, "REGION_KEY")
    if d.empty:
        return {"items": [], "aggregation": aggregation}
    vars_ = [c for c in ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "PRECTOTCORR"] if c in d.columns]
    if aggregation == "monthly":
        d["date"] = d["DATE"].dt.to_period("M").astype(str)
        out = d.groupby("date")[vars_].mean().reset_index()
    else:
        d["date"] = d["DATE"].dt.strftime("%Y-%m-%d")
        out = d.groupby("date")[vars_].mean().reset_index()
    out[vars_] = out[vars_].round(2)
    return {"items": records(out), "aggregation": aggregation, "region": region or "Rata-rata regional"}

@app.get("/api/wbc/2026")
def wbc_2026(region: str = ""):
    d = wbc.copy()
    if region:
        d = region_filter(d, region, "REGION")
    d = d.sort_values(["tahun", "bulan_ke"])
    cols = ["kabupaten_kota", "tahun", "bulan_ke", "bulan", "luas_terkena_T", "luas_puso_P"]
    out = d[cols].rename(columns={
        "kabupaten_kota": "region", "luas_terkena_T": "luas_terkena_ha", "luas_puso_P": "luas_puso_ha"
    })
    out[["luas_terkena_ha", "luas_puso_ha"]] = out[["luas_terkena_ha", "luas_puso_ha"]].round(3)
    return {
        "items": records(out), "total_records": int(len(out)),
        "source": "SiPerDitTan WBC Jawa Timur 2026",
        "meaning": "Nilai mengikuti kolom luas_terkena_T dan luas_puso_P pada sumber SiPerDitTan."
    }

@app.get("/api/wbc/summary/monthly")
def wbc_monthly_summary():
    d = wbc.groupby(["tahun", "bulan_ke", "bulan"], as_index=False).agg(
        total_terkena=("luas_terkena_T", "sum"),
        total_puso=("luas_puso_P", "sum"),
        wilayah_terkena=("luas_terkena_T", lambda x: int((x > 0).sum())),
        jumlah_wilayah=("kabupaten_kota", "nunique")
    ).sort_values(["tahun", "bulan_ke"])
    d[["total_terkena", "total_puso"]] = d[["total_terkena", "total_puso"]].round(3)
    return {"items": records(d), "source": "SiPerDitTan 2026"}

@app.get("/api/wbc/summary/regions")
def wbc_region_summary(month: int = 10):
    d = wbc[wbc["bulan_ke"] == month].copy()
    out = d.groupby(["REGION", "kabupaten_kota"], as_index=False).agg(
        luas_terkena=("luas_terkena_T", "sum"),
        luas_puso=("luas_puso_P", "sum")
    ).sort_values("luas_terkena", ascending=False)
    out[["luas_terkena", "luas_puso"]] = out[["luas_terkena", "luas_puso"]].round(3)
    return {"month": month, "items": records(out)}

@app.get("/api/forecast/bbpopt")
def bbpopt_forecast(region: str = "", year: int = 0):
    d = forecast.copy()
    if region:
        d = d[d["kabupaten_kota"].map(normalize_region) == normalize_region(region)]
    if year and "tahun_publikasi_sumber" in d.columns:
        d = d[d["tahun_publikasi_sumber"] == year]
    return {"items": records(d), "total_records": int(len(d)), "warning": "Data prakiraan BBPOPT bukan observasi aktual rutin."}

@app.get("/api/model/metrics")
def model_metrics():
    cls_path = DATA / "wbc_two_stage_classification_metrics.csv"
    reg_path = DATA / "wbc_two_stage_regression_metrics.csv"
    comb_path = DATA / "wbc_two_stage_combined_metrics.csv"
    def load(path):
        return records(pd.read_csv(path)) if path.exists() else []
    return {
        "classification": load(cls_path),
        "regression": load(reg_path),
        "combined": load(comb_path),
        "status": "eksperimental",
        "note": "Evaluasi awal menggunakan data aktual WBC 2026. Belum merupakan validasi temporal multi-tahun dan belum layak untuk keputusan operasional."
    }

# ============================================================
# PESTCYCLE AI - MACHINE LEARNING PREDICTION API
# ============================================================

ML_DATASET = DATA / "wbc_next_month_ml_dataset_2026.csv"
MODEL_DIR = BASE / "models" / "two_stage"

@app.get("/api/wbc/predict")
def predict_wbc(
    region: str,
    start_date: str,
    end_date: str
):
    try:
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)

        if start > end:
            raise HTTPException(
                status_code=400,
                detail="Tanggal awal tidak boleh melebihi tanggal akhir."
            )

        if not ML_DATASET.exists():
            raise HTTPException(
                status_code=404,
                detail="Dataset machine learning tidak ditemukan."
            )

        classifier_path = MODEL_DIR / "random_forest_classifier.joblib"
        regressor_path = MODEL_DIR / "dummy_regressor.joblib"

        if not classifier_path.exists() or not regressor_path.exists():
            raise HTTPException(
                status_code=404,
                detail="File model machine learning tidak ditemukan."
            )

        classifier = joblib.load(classifier_path)
        regressor = joblib.load(regressor_path)

        dataset = pd.read_csv(ML_DATASET)

        if "REGION_KEY" not in dataset.columns:
            raise ValueError("Kolom REGION_KEY tidak ditemukan.")

        selected = dataset[
            dataset["REGION_KEY"].map(normalize_region)
            == normalize_region(region)
        ].copy()

        if selected.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Data fitur wilayah {region} tidak ditemukan."
            )

        selected["YEAR"] = pd.to_numeric(
            selected["YEAR"], errors="coerce"
        )
        selected["MONTH"] = pd.to_numeric(
            selected["MONTH"], errors="coerce"
        )

        selected = selected.sort_values(
            ["YEAR", "MONTH"]
        )

        base_row = selected.iloc[-1].copy()

        excluded = {
            "WBC_AFFECTED_HA",
            "WBC_PUSO_HA",
            "DATA_SPLIT",
            "TARGET_OCCURRENCE",
            "REGION_KEY"
        }

        if hasattr(classifier, "feature_names_in_"):
            feature_cols = list(classifier.feature_names_in_)
        else:
            feature_cols = [
                c for c in selected.columns
                if c not in excluded
            ]

        missing = [
            c for c in feature_cols
            if c not in selected.columns
        ]

        if missing:
            raise ValueError(
                f"Fitur model tidak tersedia: {missing}"
            )

        if hasattr(regressor, "feature_names_in_"):
            reg_features = list(regressor.feature_names_in_)
            if reg_features != feature_cols:
                raise ValueError(
                    "Fitur classifier dan regressor berbeda."
                )

        months = pd.period_range(
            start=start,
            end=end,
            freq="M"
        )

        results = []
        previous_prediction = float(
            base_row.get("WBC_AFFECTED_HA_LAG1", 0) or 0
        )

        for period in months:
            row = base_row.copy()

            month = int(period.month)
            year = int(period.year)

            row["YEAR"] = year
            row["MONTH"] = month
            row["MONTH_SIN"] = np.sin(
                2 * np.pi * month / 12
            )
            row["MONTH_COS"] = np.cos(
                2 * np.pi * month / 12
            )

            if "WBC_AFFECTED_HA_LAG1" in row.index:
                row["WBC_AFFECTED_HA_LAG1"] = previous_prediction

            X = pd.DataFrame(
                [[row[c] for c in feature_cols]],
                columns=feature_cols
            )

            probability = float(
                classifier.predict_proba(X)[0][
                    list(classifier.classes_).index(1)
                ]
            )

            regression_value = float(
                regressor.predict(X)[0]
            )

            regression_value = max(0, regression_value)

            predicted_area = (
                regression_value
                if probability >= 0.5
                else 0.0
            )

            previous_prediction = predicted_area

            results.append({
                "date": str(period),
                "year": year,
                "month": month,
                "probability": round(probability, 4),
                "predicted_affected_ha": round(
                    predicted_area, 3
                ),
                "risk": (
                    "Terdapat potensi serangan"
                    if probability >= 0.5
                    else "Potensi serangan rendah"
                )
            })

        return {
            "success": True,
            "region": region,
            "start_date": start_date,
            "end_date": end_date,
            "model": "Random Forest Classifier + Dummy Regressor",
            "total_periods": len(results),
            "items": results,
            "total_predicted_ha": round(
                sum(x["predicted_affected_ha"] for x in results),
                3
            )
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Prediksi gagal: {str(error)}"
        )

