
# ============================================================
# PESTCYCLE AI
# COMPLETE BACKEND API
# VERSION 2.3.0
# ============================================================

import logging
import calendar
from pathlib import Path
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# 1. LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

logger = logging.getLogger("pestcycle")


# ============================================================
# 2. DIRECTORY CONFIGURATION
# ============================================================

# ============================================================
# 2. DIRECTORY CONFIGURATION
# ============================================================

BASE = Path(__file__).resolve().parent

DATA = BASE / "data"

MODEL_DIR = BASE / "models" / "two_stage"

WEATHER_FILE = DATA / "nasa_power_daily_38_regions_2020_2026.csv"

WBC_FILE = DATA / "wbc_siperdittan_2026_clean.csv"

FORECAST_FILE = DATA / "wbc_bbopt_forecast_clean.csv"

ML_DATASET = DATA / "wbc_next_month_ml_dataset_2026.csv"

CLASSIFIER_FILE = MODEL_DIR / "random_forest_classifier.joblib"

REGRESSOR_FILE = MODEL_DIR / "dummy_regressor.joblib"

APP_VERSION = "2.3.0"

MODEL_STATUS = "experimental_not_production_validated"

DATA = BASE / "data"
MODEL_DIR = BASE / "models" / "two_stage"

WEATHER_FILE = DATA / "nasa_power_daily_38_regions_2020_2026.csv"

WBC_FILE = DATA / "wbc_siperdittan_2026_clean.csv"

FORECAST_FILE = DATA / "wbc_bbopt_forecast_clean.csv"

ML_DATASET = DATA / "wbc_next_month_ml_dataset_2026.csv"

CLASSIFIER_FILE = MODEL_DIR / "random_forest_classifier.joblib"

REGRESSOR_FILE = MODEL_DIR / "dummy_regressor.joblib"

APP_VERSION = "2.3.0"

MODEL_STATUS = "experimental_not_production_validated"


# ============================================================
# 3. UTILITY FUNCTIONS
# ============================================================

def normalize_region(value):

    if pd.isna(value):
        return ""

    return " ".join(
        str(value).strip().upper().split()
    )


def records(df):

    return (
        df.astype(object)
        .where(pd.notna(df), None)
        .to_dict(orient="records")
    )


def safe_float(value, default=0.0):

    try:

        value = float(value)

        if np.isfinite(value):
            return value

    except (TypeError, ValueError):

        pass

    return default


def require_columns(df, columns, dataset_name):

    missing = [
        col for col in columns
        if col not in df.columns
    ]

    if missing:

        raise RuntimeError(
            f"Kolom {dataset_name} tidak ditemukan: {missing}"
        )


def filter_region(df, region, column="REGION"):

    if not region:
        return df.copy()

    if column not in df.columns:

        return df.iloc[0:0].copy()

    key = normalize_region(region)

    return df[
        df[column].map(normalize_region) == key
    ].copy()


def load_csv(path, name):

    if not path.exists():

        raise FileNotFoundError(
            f"File {name} tidak ditemukan: {path}"
        )

    logger.info("Memuat %s", name)

    return pd.read_csv(path)


# ============================================================
# 4. LOAD NASA POWER
# ============================================================

weather = load_csv(
    WEATHER_FILE,
    "NASA POWER"
)

require_columns(
    weather,
    ["DATE"],
    "NASA POWER"
)

weather["DATE"] = pd.to_datetime(
    weather["DATE"],
    errors="coerce"
)

weather = weather.dropna(
    subset=["DATE"]
).copy()

weather = weather.sort_values(
    "DATE"
).reset_index(drop=True)


if "REGION" in weather.columns:

    weather["REGION_KEY"] = (
        weather["REGION"].map(normalize_region)
    )

elif "REGION_KEY" in weather.columns:

    weather["REGION_KEY"] = (
        weather["REGION_KEY"].map(normalize_region)
    )

else:

    weather["REGION_KEY"] = ""


WEATHER_HAS_REGION = (
    weather["REGION_KEY"].ne("").any()
)


WEATHER_VARIABLES = [
    "T2M",
    "T2M_MAX",
    "T2M_MIN",
    "RH2M",
    "PRECTOTCORR"
]

for col in WEATHER_VARIABLES:

    if col in weather.columns:

        weather[col] = pd.to_numeric(
            weather[col],
            errors="coerce"
        )


# ============================================================
# 5. LOAD SIPERDITTAN WBC
# ============================================================

wbc = load_csv(
    WBC_FILE,
    "SiPerDitTan"
)

require_columns(
    wbc,
    [
        "kabupaten_kota",
        "tahun",
        "bulan_ke",
        "bulan",
        "luas_terkena_T",
        "luas_puso_P"
    ],
    "SiPerDitTan"
)

wbc["kabupaten_kota"] = (
    wbc["kabupaten_kota"].astype(str).str.strip()
)

wbc["REGION"] = (
    wbc["kabupaten_kota"].map(normalize_region)
)

for col in [
    "tahun",
    "bulan_ke",
    "luas_terkena_T",
    "luas_puso_P"
]:

    wbc[col] = pd.to_numeric(
        wbc[col],
        errors="coerce"
    )

wbc = wbc.dropna(
    subset=[
        "tahun",
        "bulan_ke",
        "luas_terkena_T",
        "luas_puso_P"
    ]
).copy()

wbc["tahun"] = wbc["tahun"].astype(int)

wbc["bulan_ke"] = wbc["bulan_ke"].astype(int)


# ============================================================
# 6. LOAD BBPOPT
# ============================================================

forecast = load_csv(
    FORECAST_FILE,
    "BBPOPT"
)

require_columns(
    forecast,
    ["kabupaten_kota"],
    "BBPOPT"
)

forecast["kabupaten_kota"] = (
    forecast["kabupaten_kota"].astype(str).str.strip()
)


# ============================================================
# 7. LOAD ML DATASET
# ============================================================

def load_ml_data():

    if not ML_DATASET.exists():

        logger.warning(
            "Dataset machine learning belum tersedia."
        )

        return pd.DataFrame()

    df = pd.read_csv(ML_DATASET)

    if "REGION_KEY" in df.columns:

        df["REGION_KEY"] = (
            df["REGION_KEY"].map(normalize_region)
        )

    return df


ml_dataset = load_ml_data()


# ============================================================
# 8. REGIONS
# ============================================================

REGIONS = sorted(
    wbc["kabupaten_kota"].dropna().unique().tolist(),
    key=str.casefold
)


# ============================================================
# 9. FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="PestCycle AI API",
    description=(
        "API pemantauan Wereng Batang Cokelat "
        "menggunakan NASA POWER, SiPerDitTan, "
        "BBPOPT, dan Machine Learning."
    ),
    version=APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# ============================================================
# 10. ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "application": "PestCycle AI",
        "version": APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }


# ============================================================
# 11. HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {

        "status": "ok",

        "application": "PestCycle AI",

        "version": APP_VERSION,

        "weather_rows": int(len(weather)),

        "weather_start": weather["DATE"].min().strftime("%Y-%m-%d"),

        "weather_end": weather["DATE"].max().strftime("%Y-%m-%d"),

        "weather_regions": (
            int(weather["REGION_KEY"].nunique())
            if WEATHER_HAS_REGION else 0
        ),

        "wbc_2026_rows": int(len(wbc)),

        "wbc_regions": int(wbc["REGION"].nunique()),

        "bbpopt_rows": int(len(forecast)),

        "model_status": MODEL_STATUS,

        "datasets": {

            "nasa_power": {
                "file": WEATHER_FILE.name,
                "rows": int(len(weather)),
                "regions": (
                    int(weather["REGION_KEY"].nunique())
                    if WEATHER_HAS_REGION else 0
                )
            },

            "siperdittan_2026": {
                "file": WBC_FILE.name,
                "rows": int(len(wbc)),
                "regions": int(wbc["REGION"].nunique())
            },

            "bbpopt": {
                "file": FORECAST_FILE.name,
                "rows": int(len(forecast))
            }
        },

        "prediction": {
            "dataset_exists": ML_DATASET.exists(),
            "classifier_exists": CLASSIFIER_FILE.exists(),
            "regressor_exists": REGRESSOR_FILE.exists()
        },

        "notice": (
            "Data aktual SiPerDitTan dan prakiraan BBPOPT "
            "merupakan sumber berbeda. Model prediksi "
            "masih bersifat eksperimental."
        )
    }


# ============================================================
# 12. REGIONS API
# ============================================================

@app.get("/api/regions")
def get_regions():

    return {
        "total_regions": len(REGIONS),
        "regions": REGIONS
    }

# ============================================================
# 13. NASA POWER - WEATHER LATEST
# ============================================================

@app.get("/api/weather/latest")
def weather_latest(region: str = ""):

    d = weather.copy()

    if region:

        if not WEATHER_HAS_REGION:

            raise HTTPException(
                status_code=400,
                detail="Identitas wilayah tidak tersedia pada dataset cuaca."
            )

        d = filter_region(
            d,
            region,
            "REGION_KEY"
        )

    if d.empty:

        raise HTTPException(
            status_code=404,
            detail="Data cuaca tidak ditemukan."
        )

    latest_date = d["DATE"].max()

    latest = d[
        d["DATE"] == latest_date
    ]

    columns = [
        col for col in WEATHER_VARIABLES
        if col in latest.columns
    ]

    values = latest[columns].mean(
        numeric_only=True
    )

    return {

        "date": latest_date.strftime("%Y-%m-%d"),

        "region": region or "Rata-rata regional",

        "regions_included": (
            int(latest["REGION_KEY"].nunique())
            if WEATHER_HAS_REGION else None
        ),

        "values": {
            key: round(float(value), 2)
            if pd.notna(value) else None
            for key, value in values.items()
        }
    }


# ============================================================
# 14. NASA POWER - WEATHER SERIES
# ============================================================

@app.get("/api/weather/series")
def weather_series(

    start: str = "2020-01-01",

    end: str = "2026-10-31",

    aggregation: str = Query(
        default="monthly",
        pattern="^(daily|monthly)$"
    ),

    region: str = ""

):

    try:

        start_date = pd.to_datetime(start)

        end_date = pd.to_datetime(end)

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Format tanggal tidak valid."
        )

    if start_date > end_date:

        raise HTTPException(
            status_code=400,
            detail="Tanggal awal melebihi tanggal akhir."
        )

    d = weather[
        (weather["DATE"] >= start_date)
        & (weather["DATE"] <= end_date)
    ].copy()

    if region:

        if not WEATHER_HAS_REGION:

            raise HTTPException(
                status_code=400,
                detail="Data cuaca tidak memiliki identitas wilayah."
            )

        d = filter_region(
            d,
            region,
            "REGION_KEY"
        )

    if d.empty:

        return {
            "items": [],
            "total_records": 0,
            "aggregation": aggregation,
            "region": region
        }

    variables = [
        col for col in WEATHER_VARIABLES
        if col in d.columns
    ]

    if aggregation == "monthly":

        d["date"] = (
            d["DATE"].dt.to_period("M").astype(str)
        )

    else:

        d["date"] = (
            d["DATE"].dt.strftime("%Y-%m-%d")
        )

    result = (
        d.groupby("date")[variables]
        .mean()
        .reset_index()
        .sort_values("date")
    )

    result[variables] = result[variables].round(2)

    return {

        "items": records(result),

        "total_records": int(len(result)),

        "aggregation": aggregation,

        "region": region or "Rata-rata regional",

        "source": WEATHER_FILE.name
    }


# ============================================================
# 15. WBC ACTUAL 2026
# ============================================================

@app.get("/api/wbc/2026")
def wbc_2026(region: str = ""):

    d = filter_region(
        wbc,
        region,
        "REGION"
    )

    d = d.sort_values(
        ["tahun", "bulan_ke"]
    )

    result = d[
        [
            "kabupaten_kota",
            "tahun",
            "bulan_ke",
            "bulan",
            "luas_terkena_T",
            "luas_puso_P"
        ]
    ].rename(
        columns={
            "kabupaten_kota": "region",
            "luas_terkena_T": "luas_terkena_ha",
            "luas_puso_P": "luas_puso_ha"
        }
    )

    result[
        ["luas_terkena_ha", "luas_puso_ha"]
    ] = result[
        ["luas_terkena_ha", "luas_puso_ha"]
    ].round(3)

    return {

        "items": records(result),

        "total_records": int(len(result)),

        "source": "SiPerDitTan WBC Jawa Timur 2026",

        "meaning": (
            "Nilai mengikuti kolom luas_terkena_T "
            "dan luas_puso_P pada sumber SiPerDitTan."
        )
    }


# ============================================================
# 16. WBC MONTHLY SUMMARY
# ============================================================

@app.get("/api/wbc/summary/monthly")
def wbc_monthly_summary():

    result = (

        wbc.groupby(
            ["tahun", "bulan_ke", "bulan"],
            as_index=False
        )

        .agg(

            total_terkena=(
                "luas_terkena_T",
                "sum"
            ),

            total_puso=(
                "luas_puso_P",
                "sum"
            ),

            wilayah_terkena=(
                "luas_terkena_T",
                lambda x: int((x > 0).sum())
            ),

            jumlah_wilayah=(
                "kabupaten_kota",
                "nunique"
            )
        )

        .sort_values(
            ["tahun", "bulan_ke"]
        )
    )

    result[
        ["total_terkena", "total_puso"]
    ] = result[
        ["total_terkena", "total_puso"]
    ].round(3)

    return {

        "items": records(result),

        "total_records": int(len(result)),

        "source": "SiPerDitTan 2026"
    }


# ============================================================
# 17. WBC REGIONAL SUMMARY
# ============================================================

@app.get("/api/wbc/summary/regions")
def wbc_region_summary(

    month: int = Query(
        default=10,
        ge=1,
        le=12
    )

):

    d = wbc[
        wbc["bulan_ke"] == month
    ].copy()

    result = (

        d.groupby(
            ["REGION", "kabupaten_kota"],
            as_index=False
        )

        .agg(

            luas_terkena=(
                "luas_terkena_T",
                "sum"
            ),

            luas_puso=(
                "luas_puso_P",
                "sum"
            )
        )

        .sort_values(
            "luas_terkena",
            ascending=False
        )
    )

    result[
        ["luas_terkena", "luas_puso"]
    ] = result[
        ["luas_terkena", "luas_puso"]
    ].round(3)

    return {

        "month": month,

        "items": records(result),

        "total_records": int(len(result)),

        "source": "SiPerDitTan 2026"
    }


# ============================================================
# 18. BBPOPT FORECAST
# ============================================================

@app.get("/api/forecast/bbpopt")
def bbpopt_forecast(

    region: str = "",

    year: int = 0

):

    d = forecast.copy()

    if region:

        d = d[
            d["kabupaten_kota"].map(normalize_region)
            == normalize_region(region)
        ]

    year_column = "tahun_publikasi_sumber"

    if year and year_column in d.columns:

        d[year_column] = pd.to_numeric(
            d[year_column],
            errors="coerce"
        )

        d = d[
            d[year_column] == year
        ]

    return {

        "items": records(d),

        "total_records": int(len(d)),

        "region": region or "Semua wilayah",

        "year": year if year else None,

        "source": FORECAST_FILE.name,

        "warning": (
            "Prakiraan BBPOPT bukan data observasi "
            "aktual SiPerDitTan."
        )
    }


# ============================================================
# 19. MODEL METRICS
# ============================================================

@app.get("/api/model/metrics")
def model_metrics():

    classification_file = (
        DATA / "wbc_two_stage_classification_metrics.csv"
    )

    regression_file = (
        DATA / "wbc_two_stage_regression_metrics.csv"
    )

    combined_file = (
        DATA / "wbc_two_stage_combined_metrics.csv"
    )

    def load_metrics(path):

        if not path.exists():

            return []

        return records(
            pd.read_csv(path)
        )

    return {

        "classification": load_metrics(
            classification_file
        ),

        "regression": load_metrics(
            regression_file
        ),

        "combined": load_metrics(
            combined_file
        ),

        "status": "eksperimental",

        "note": (
            "Evaluasi awal menggunakan data aktual WBC 2026. "
            "Belum merupakan validasi temporal multi-tahun "
            "dan belum layak untuk keputusan operasional."
        )
    }

# ============================================================
# 20. MACHINE LEARNING CONFIGURATION
# ============================================================

PREDICTION_THRESHOLD = 0.5

CLASSIFIER_NAME = "Random Forest Classifier"

REGRESSOR_NAME = "Dummy Regressor"


# ============================================================
# 21. LOAD MACHINE LEARNING MODELS
# ============================================================

@lru_cache(maxsize=1)
def load_ml_models():

    if not CLASSIFIER_FILE.exists():

        raise FileNotFoundError(
            f"Classifier tidak ditemukan: {CLASSIFIER_FILE}"
        )

    if not REGRESSOR_FILE.exists():

        raise FileNotFoundError(
            f"Regressor tidak ditemukan: {REGRESSOR_FILE}"
        )

    classifier = joblib.load(
        CLASSIFIER_FILE
    )

    regressor = joblib.load(
        REGRESSOR_FILE
    )

    if not hasattr(classifier, "predict_proba"):

        raise ValueError(
            "Classifier tidak mendukung predict_proba."
        )

    if not hasattr(regressor, "predict"):

        raise ValueError(
            "Regressor tidak mendukung predict."
        )

    logger.info("Classifier berhasil dimuat.")

    logger.info("Regressor berhasil dimuat.")

    return classifier, regressor


# ============================================================
# 22. GET MODEL FEATURE NAMES
# ============================================================

def get_model_features(model, model_name):

    if not hasattr(model, "feature_names_in_"):

        raise ValueError(
            f"{model_name} tidak mempunyai feature_names_in_."
        )

    return list(
        model.feature_names_in_
    )


# ============================================================
# 23. VALIDATE MODEL PREPROCESSING
# ============================================================

def validate_model_preprocessing(
    classifier,
    regressor
):

    classifier_features = get_model_features(
        classifier,
        "Classifier"
    )

    regressor_features = get_model_features(
        regressor,
        "Regressor"
    )

    if classifier_features != regressor_features:

        raise ValueError(
            "Fitur atau urutan fitur classifier "
            "dan regressor berbeda."
        )

    if "REGION_KEY" not in classifier_features:

        raise ValueError(
            "REGION_KEY tidak ditemukan pada fitur model."
        )

    # Jangan melakukan encoding numerik manual.
    # Pipeline training harus menangani kategorikal.

    for model, name in [
        (classifier, "Classifier"),
        (regressor, "Regressor")
    ]:

        if not hasattr(model, "named_steps"):

            raise ValueError(
                f"{name} bukan Pipeline. "
                "Preprocessing asli tidak dapat dipastikan. "
                "Prediksi dihentikan untuk mencegah "
                "penggunaan encoding wilayah yang keliru."
            )

    return classifier_features


# ============================================================
# 24. VALIDATE PREDICTION DATASET
# ============================================================

def validate_prediction_dataset(dataset, feature_cols):

    missing = [
        col for col in feature_cols
        if col not in dataset.columns
    ]

    if missing:

        raise ValueError(
            f"Kolom dataset tidak lengkap: {missing}"
        )

    if "REGION_KEY" not in dataset.columns:

        raise ValueError(
            "REGION_KEY tidak ditemukan."
        )

    if dataset.empty:

        raise ValueError(
            "Dataset machine learning kosong."
        )

    numeric_columns = [
        col for col in feature_cols
        if col != "REGION_KEY"
    ]

    for col in numeric_columns:

        dataset[col] = pd.to_numeric(
            dataset[col],
            errors="coerce"
        )

    return dataset


# ============================================================
# 25. CREATE PREDICTION INPUT
# ============================================================

def create_prediction_input(
    row,
    feature_cols
):

    X = pd.DataFrame(
        [[row[col] for col in feature_cols]],
        columns=feature_cols
    )

    # REGION_KEY harus tetap string.
    X["REGION_KEY"] = (
        X["REGION_KEY"]
        .map(normalize_region)
    )

    numeric_columns = [
        col for col in feature_cols
        if col != "REGION_KEY"
    ]

    for col in numeric_columns:

        X[col] = pd.to_numeric(
            X[col],
            errors="coerce"
        )

    if X["REGION_KEY"].isna().any():

        raise ValueError(
            "REGION_KEY kosong."
        )

    if (X["REGION_KEY"] == "").any():

        raise ValueError(
            "REGION_KEY tidak valid."
        )

    if X[numeric_columns].isna().any().any():

        bad_columns = X[numeric_columns].columns[
            X[numeric_columns].isna().any()
        ].tolist()

        raise ValueError(
            f"Fitur numerik kosong: {bad_columns}"
        )

    if not np.isfinite(
        X[numeric_columns].to_numpy(dtype=float)
    ).all():

        raise ValueError(
            "Fitur mengandung nilai tak hingga."
        )

    return X


# ============================================================
# 26. PREDICTION ENDPOINT
# ============================================================

@app.get("/api/wbc/predict")
def predict_wbc(

    region: str = Query(
        ...,
        min_length=1
    ),

    start_date: str = Query(
        ...,
        description="YYYY-MM-DD"
    ),

    end_date: str = Query(
        ...,
        description="YYYY-MM-DD"
    )

):

    # --------------------------------------------------------
    # A. VALIDATE DATE
    # --------------------------------------------------------

    try:

        start = pd.to_datetime(
            start_date,
            errors="raise"
        )

        end = pd.to_datetime(
            end_date,
            errors="raise"
        )

    except Exception:

        raise HTTPException(
            status_code=400,
            detail="Tanggal harus menggunakan format YYYY-MM-DD."
        )

    if start > end:

        raise HTTPException(
            status_code=400,
            detail="Tanggal awal melebihi tanggal akhir."
        )

    normalized_region = normalize_region(
        region
    )

    if not normalized_region:

        raise HTTPException(
            status_code=400,
            detail="Wilayah wajib diisi."
        )

    # --------------------------------------------------------
    # B. LOAD DATASET
    # --------------------------------------------------------

    if ml_dataset.empty:

        raise HTTPException(
            status_code=500,
            detail="Dataset machine learning kosong."
        )

    dataset = ml_dataset.copy()

    # --------------------------------------------------------
    # C. LOAD MODELS
    # --------------------------------------------------------

    try:

        classifier, regressor = load_ml_models()

        feature_cols = validate_model_preprocessing(
            classifier,
            regressor
        )

        dataset = validate_prediction_dataset(
            dataset,
            feature_cols
        )

    except Exception as error:

        logger.exception(
            "Gagal menyiapkan model prediksi."
        )

        raise HTTPException(
            status_code=500,
            detail=f"Konfigurasi model tidak valid: {error}"
        )

    # --------------------------------------------------------
    # D. FILTER REGION
    # --------------------------------------------------------

    selected = dataset[
        dataset["REGION_KEY"] == normalized_region
    ].copy()

    if selected.empty:

        raise HTTPException(
            status_code=404,
            detail=(
                f"Data fitur wilayah {normalized_region} "
                "tidak ditemukan."
            )
        )

    # --------------------------------------------------------
    # E. SORT HISTORICAL DATA
    # --------------------------------------------------------

    selected["YEAR"] = pd.to_numeric(
        selected["YEAR"],
        errors="coerce"
    )

    selected["MONTH"] = pd.to_numeric(
        selected["MONTH"],
        errors="coerce"
    )

    selected = selected.dropna(
        subset=["YEAR", "MONTH"]
    )

    selected = selected.sort_values(
        ["YEAR", "MONTH"]
    )

    if selected.empty:

        raise HTTPException(
            status_code=500,
            detail="Data historis tidak valid."
        )

    base_row = selected.iloc[-1].copy()

    # --------------------------------------------------------
    # F. CREATE MONTHLY PERIODS
    # --------------------------------------------------------

    periods = pd.period_range(
        start=start.to_period("M"),
        end=end.to_period("M"),
        freq="M"
    )

    if len(periods) == 0:

        raise HTTPException(
            status_code=400,
            detail="Periode prediksi tidak tersedia."
        )

    # --------------------------------------------------------
    # G. GET POSITIVE CLASS
    # --------------------------------------------------------

    classes = list(
        classifier.classes_
    )

    positive_indices = [
        i for i, value in enumerate(classes)
        if value == 1 or str(value) == "1"
    ]

    if not positive_indices:

        raise HTTPException(
            status_code=500,
            detail="Kelas positif 1 tidak ditemukan."
        )

    positive_index = positive_indices[0]

    # --------------------------------------------------------
    # H. INITIAL LAG
    # --------------------------------------------------------

    previous_prediction = safe_float(
        base_row.get(
            "WBC_AFFECTED_HA_LAG1",
            0
        )
    )

    results = []

    # --------------------------------------------------------
    # I. MONTHLY PREDICTION
    # --------------------------------------------------------

    for period in periods:

        year = int(period.year)

        month = int(period.month)

        row = base_row.copy()

        row["YEAR"] = year

        row["MONTH"] = month

        row["MONTH_SIN"] = np.sin(
            2 * np.pi * month / 12
        )

        row["MONTH_COS"] = np.cos(
            2 * np.pi * month / 12
        )

        if "WBC_AFFECTED_HA_LAG1" in row.index:

            row["WBC_AFFECTED_HA_LAG1"] = (
                previous_prediction
            )

        try:

            X = create_prediction_input(
                row,
                feature_cols
            )

            # Pipeline menjalankan preprocessing
            # kategorikal sesuai proses training.

            probabilities = (
                classifier.predict_proba(X)[0]
            )

            probability = float(
                probabilities[positive_index]
            )

            regression_value = float(
                regressor.predict(X)[0]
            )

            if not np.isfinite(probability):

                raise ValueError(
                    "Probabilitas tidak valid."
                )

            if not np.isfinite(regression_value):

                raise ValueError(
                    "Nilai regresi tidak valid."
                )

            probability = min(
                1.0,
                max(0.0, probability)
            )

            regression_value = max(
                0.0,
                regression_value
            )

            predicted_area = (
                regression_value
                if probability >= PREDICTION_THRESHOLD
                else 0.0
            )

            previous_prediction = predicted_area

            results.append({

                "date": str(period),

                "year": year,

                "month": month,

                "probability": round(
                    probability,
                    4
                ),

                "predicted_affected_ha": round(
                    predicted_area,
                    3
                ),

                "risk": (
                    "Terdapat potensi serangan"
                    if probability >= PREDICTION_THRESHOLD
                    else "Potensi serangan rendah"
                )
            })

        except Exception as error:

            logger.exception(
                "Prediksi gagal pada periode %s",
                period
            )

            raise HTTPException(
                status_code=500,
                detail=(
                    f"Prediksi gagal pada periode {period}: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # J. RESPONSE
    # --------------------------------------------------------

    return {

        "success": True,

        "region": normalized_region,

        "start_date": start_date,

        "end_date": end_date,

        "model": (
            f"{CLASSIFIER_NAME} + {REGRESSOR_NAME}"
        ),

        "total_periods": len(results),

        "items": results,

        "total_predicted_ha": round(
            sum(
                item["predicted_affected_ha"]
                for item in results
            ),
            3
        ),

        "status": "experimental",

        "warning": (
            "Prediksi merupakan estimasi eksperimental. "
            "Hasil belum divalidasi untuk keputusan operasional."
        )
    }


# ============================================================
# 27. END OF PESTCYCLE AI API
# ============================================================

logger.info(
    "PestCycle AI API %s berhasil diinisialisasi.",
    APP_VERSION
)
