import React, { useEffect, useMemo, useState } from "react";
import {
  Bell,
  MapPin,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Sprout,
  Thermometer,
  Droplets,
  CloudRain,
  Bug,
  TrendingUp,
  ShieldAlert,
  Leaf,
  CheckCircle2,
  Map,
  Activity,
  X,
  Info
} from "lucide-react";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip
} from "recharts";

const MAP_WIDTH = 1200;
const MAP_HEIGHT = 760;
const MAP_JSON = "/koordinat-peta-jawa-timur.json";

const fmt = (value, digits = 1) =>
  Number.isFinite(Number(value))
    ? Number(value).toLocaleString("en-US", {
        maximumFractionDigits: digits
      })
    : "—";

const riskColors = {
  Low: "#2eaa63",
  Moderate: "#f2c532",
  High: "#f28a24",
  Critical: "#e63d3d",
  "No data": "#8da798"
};

let regionRisk = [];

let trend = [
  { day: "1 Des", value: 228 },
  { day: "3 Des", value: 265 },
  { day: "5 Des", value: 301 },
  { day: "7 Des", value: 348 },
  { day: "9 Des", value: 512 },
  { day: "11 Des", value: 486 },
  { day: "13 Des", value: 438 },
  { day: "15 Des", value: 392 }
];

function getMapRisk(name, dataList = regionRisk) {
  const data = dataList.find(item =>
    String(item.name).trim().toUpperCase() ===
    String(name).trim().toUpperCase()
  );

  if (!data || data.hasData === false) {
    return {
      name,
      score: null,
      value: null,
      puso: 0,
      label: "No data",
      color: riskColors["No data"],
      filter: "none",
      hasData: false
    };
  }

  const value = Number(data.value ?? data.affectedHa ?? 0);
  const puso = Number(data.puso || 0);
  const score = Number(data.score ?? 0);

  // Jika data tersedia dan tidak ditemukan serangan,
  // wilayah langsung dikategorikan AMAN.
  if (value <= 0 && puso <= 0) {
    return {
      ...data,
      value: 0,
      puso: 0,
      score: 0,
      label: "Safe",
      color: riskColors.Low,
      filter: "none",
      hasData: true
    };
  }

  let label = "Low";
  let color = riskColors.Low;
  let filter = "hue-rotate(35deg) saturate(1.3)";

  if (score >= 0.85) {
    label = "Critical";
    color = riskColors.Critical;
    filter = "hue-rotate(145deg) saturate(1.7)";
  } else if (score >= 0.65) {
    label = "High";
    color = riskColors.High;
    filter = "hue-rotate(115deg) saturate(1.5)";
  } else if (score >= 0.35) {
    label = "Moderate";
    color = riskColors.Moderate;
    filter = "hue-rotate(75deg) saturate(1.4)";
  }

  return {
    ...data,
    value,
    puso,
    score,
    label,
    color,
    filter,
    hasData: true
  };
}

function getRegionStyle(region) {
  const x = Number(region.x);
  const y = Number(region.y);
  const w = Number(region.w);
  const h = Number(region.h);
  const rotation = Number(region.rotation ?? 0);

  return {
    position: "absolute",
    left: `${(x / MAP_WIDTH) * 100}%`,
    top: `${(y / MAP_HEIGHT) * 100}%`,
    width: `${(w / MAP_WIDTH) * 100}%`,
    height: `${(h / MAP_HEIGHT) * 100}%`,
    boxSizing: "border-box",
    transform: `rotate(${rotation}deg)`,
    transformOrigin: "center center",
    padding: 0,
    margin: 0,
    border: 0,
    borderRadius: 0,
    background: "transparent",
    overflow: "visible",
    lineHeight: 0
  };
}

function EastJavaMap({
  selected,
  onSelect,
  mapRegions = [],
  riskData = [],
  large = false
}) {
  const selectedRisk = getMapRisk(selected, riskData);

  return (
    <div
      className={`east-java-map image-map ${
        large ? "map-large" : ""
      }`}
      role="group"
      aria-label="Interactive map of East Java’s 38 regencies and cities"
      style={{
        position: "relative",
        width: "100%",
        height: "auto",
        minHeight: 0,
        aspectRatio: `${MAP_WIDTH} / ${MAP_HEIGHT}`,
        overflow: "hidden",
        isolation: "isolate",
        background: "#ffffff"
      }}
    >
      {mapRegions.length === 0 && (
        <div className="map-loading-message">
          Memuat koordinat peta...
        </div>
      )}

      {mapRegions.map(region => {
        const risk = getMapRisk(region.name, riskData);
        const isSelected = region.name === selected;

        return (
          <button
            key={region.name}
            type="button"
            className={`map-region ${
              isSelected ? "selected" : ""
            }`}
            style={{
              ...getRegionStyle(region),
              zIndex: isSelected ? 100 : 1,
              cursor: "pointer",
              background: "transparent"
            }}
            onClick={() => onSelect?.(region.name)}
            title={`${region.name} - ${risk.label}`}
            aria-label={`${region.name}, ${risk.label}`}
            aria-pressed={isSelected}
          >
            <img
              src={`/wilayah-jatim/${region.file}.png`}
              alt={region.name}
              draggable="false"
              loading="eager"
              style={{
                display: "block",
                width: "100%",
                height: "calc(100% - 17px)",
                objectFit: "contain",
                objectPosition: "center",
                filter: risk.filter,
                pointerEvents: "none",
                userSelect: "none"
              }}
              onError={event => {
                console.error(
                  "Gagal memuat gambar:",
                  region.name,
                  event.currentTarget.src
                );
                event.currentTarget.style.opacity = "0";
              }}
            />
          </button>
        );
      })}

      <div
        className="map-selected-info"
        aria-live="polite"
      >
        <strong>{selected}</strong>

        <span style={{ color: selectedRisk.color }}>
          ● {selectedRisk.label}
        </span>

        {selectedRisk.value !== null && (
          <small>
            {selectedRisk.value} individuals/m²
          </small>
        )}
      </div>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  note,
  tone = "green"
}) {
  return (
    <div className={`metric-card tone-${tone}`}>
      <div className="metric-icon">
        <Icon size={22} />
      </div>

      <div>
        <span>{label}</span>
        <strong>{value}</strong>
        {note && <small>{note}</small>}
      </div>
    </div>
  );
}

function NotificationToast({
  onClose,
  location,
  notifications = []
}) {
  if (notifications.length === 0) return null;

  return (
    <div
      className="toast"
      style={{
        borderLeftColor: "#f28a24"
      }}
    >
      <div className="toast-icon">
        <Bell size={19} />
      </div>

      <div className="toast-copy">
        <strong>
          BPH Alert · {location}
        </strong>

        <span>
          {notifications[0].message}
        </span>
      </div>

      <button
        className="icon-button toast-close"
        onClick={onClose}
        aria-label="Close notification"
      >
        <X size={17} />
      </button>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState("mine");

  const [clockNow, setClockNow] = useState(
    () => new Date()
  );

  const [locationStatus, setLocationStatus] = useState(
    "Detecting location..."
  );

  const [apiReady, setApiReady] = useState(false);
  const [apiError, setApiError] = useState("");
  const [apiWeather, setApiWeather] = useState(null);
  const [apiWbc, setApiWbc] = useState([]);
  const [apiMonthly, setApiMonthly] = useState([]);
  const [apiMetrics, setApiMetrics] = useState(null);

  const [riskData, setRiskData] = useState([]);
  const [trendData, setTrendData] = useState(trend);

  const [mapRegions, setMapRegions] = useState([]);
  const [mapError, setMapError] = useState("");

  const locations = useMemo(
    () => mapRegions.map(region => region.name),
    [mapRegions]
  );

  const [myLocation, setMyLocation] = useState("Malang");

  const [predictionLocation, setPredictionLocation] =
    useState("Banyuwangi");

  const [startDate, setStartDate] =
    useState("2026-12-01");

  const [endDate, setEndDate] =
    useState("2026-12-15");

  const [toastVisible, setToastVisible] = useState(true);

  const [notificationOpen, setNotificationOpen] =
    useState(false);

  const [predicted, setPredicted] = useState(false);
const [predictionResult, setPredictionResult] = useState(null);
  useEffect(() => {
    const timer = window.setInterval(
      () => setClockNow(new Date()),
      1000
    );

    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    if (!locations.length) return;

    if (!navigator.geolocation) {
      setLocationStatus(
        "Location is unavailable on this device"
      );
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async position => {
        try {
          const { latitude, longitude } = position.coords;

          const response = await fetch(
            `https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${latitude}&lon=${longitude}&zoom=10&accept-language=id`
          );

          if (!response.ok) {
            throw new Error(
              "Unable to identify the location"
            );
          }

          const result = await response.json();
          const address = result.address || {};

          const candidates = [
            address.city,
            address.town,
            address.municipality,
            address.county,
            address.city_district,
            address.state_district
          ].filter(Boolean);

          const normalize = value =>
            String(value)
              .toLowerCase()
              .replace(/^kabupaten\s+/i, "")
              .replace(/^kota\s+/i, "")
              .trim();

          const match = locations.find(name =>
            candidates.some(
              candidate =>
                normalize(candidate) === normalize(name)
            )
          );

          if (match) {
            setMyLocation(match);
            setPredictionLocation(current => current || match);
            setLocationStatus(
              "Location detected automatically"
            );
          } else {
            setLocationStatus(
              "Location detected outside the East Java region list"
            );
          }
        } catch (error) {
          setLocationStatus(
            "Location detected, but the region could not be matched"
          );
        }
      },
      () =>
        setLocationStatus(
          "Allow location access to display your region"
        ),
      {
        enableHighAccuracy: true,
        timeout: 12000,
        maximumAge: 300000
      }
    );
  }, [locations]);
  useEffect(() => {
    let active = true;

    async function loadDashboardData() {
      try {
        const [
          healthRes,
          wbcRes,
          monthlyRes,
          metricsRes
        ] = await Promise.all([
          fetch("/api/health"),
          fetch("/api/wbc/2026"),
          fetch("/api/wbc/summary/monthly"),
          fetch("/api/model/metrics")
        ]);

        for (const response of [
          healthRes,
          wbcRes,
          monthlyRes,
          metricsRes
        ]) {
          if (!response.ok) {
            throw new Error(
              "The API could not retrieve data. Make sure the backend is running on port 8000."
            );
          }
        }

        const [
          health,
          wbcData,
          monthlyData,
          metrics
        ] = await Promise.all([
          healthRes.json(),
          wbcRes.json(),
          monthlyRes.json(),
          metricsRes.json()
        ]);

        const weatherRes = await fetch(
          "/api/weather/latest"
        );

        const weather = weatherRes.ok
          ? await weatherRes.json()
          : null;

        if (!active) return;

        setApiWeather(weather);
        setApiWbc(wbcData.items || []);
        setApiMonthly(monthlyData.items || []);
        setApiMetrics(metrics);
        setApiError("");

        // Mengambil data bulan terakhir yang tersedia.
        const latestMonth = Math.max(
          0,
          ...(wbcData.items || []).map(
            x => Number(x.bulan_ke || 0)
          )
        );

        const byRegion = new globalThis.Map();

        (wbcData.items || [])
          .filter(
            x => Number(x.bulan_ke) === latestMonth
          )
          .forEach(x => {
            const name = String(
              x.region || ""
            ).trim();

            if (!name) return;

            const key = name.toUpperCase();

            const previous = byRegion.get(key) || {
              name,
              value: 0,
              puso: 0,
              hasData: true
            };

            previous.value += Number(
              x.luas_terkena_ha || 0
            );

            previous.puso += Number(
              x.luas_puso_ha || 0
            );

            byRegion.set(key, previous);
          });

        const maxAffected = Math.max(
          0,
          ...Array.from(byRegion.values()).map(
            x => x.value
          )
        );

        const nextRiskData = Array.from(
          byRegion.values()
        ).map(x => {
          const score = maxAffected > 0
            ? x.value / maxAffected
            : 0;

          const risk = getMapRisk(
            x.name,
            [{ ...x, score }]
          );

          return {
            ...x,
            score,
            color: risk.color,
            label: risk.label,
            hasData: true
          };
        });

        regionRisk = nextRiskData;
        setRiskData(nextRiskData);

        const chosen = (wbcData.items || []).filter(
          x =>
            String(x.region).toUpperCase() ===
            "BANYUWANGI"
        );

        if (chosen.length) {
          setTrendData(
            chosen
              .sort(
                (a, b) => a.bulan_ke - b.bulan_ke
              )
              .map(x => ({
                day: x.bulan,
                value: Number(
                  x.luas_terkena_ha || 0
                )
              }))
          );
        }

        setApiReady(true);
      } catch (error) {
        if (active) {
          setApiError(
            error.message || "Failed to load API data."
          );

          setApiReady(false);
        }
      }
    }

    loadDashboardData();

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    async function loadMapCoordinates() {
      try {
        const response = await fetch(
          `${MAP_JSON}?v=1`
        );

        if (!response.ok) {
          throw new Error(
            "The map-coordinate file was not found in the public folder."
          );
        }

        const data = await response.json();

        if (
          !Array.isArray(data) ||
          data.length !== 38
        ) {
          throw new Error(
            "The JSON file must contain exactly 38 regions."
          );
        }

        const validData = data.map(
          (region, index) => {
            const valid =
              region &&
              typeof region.name === "string" &&
              typeof region.file === "string" &&
              ["x", "y", "w", "h"].every(
                key =>
                  Number.isFinite(
                    Number(region[key])
                  )
              ) &&
              Number(region.w) > 0 &&
              Number(region.h) > 0 &&
              Number.isFinite(
                Number(region.rotation ?? 0)
              );

            if (!valid) {
              throw new Error(
                `Coordinates for region ${index + 1} are invalid.`
              );
            }

            return {
              ...region,
              x: Number(region.x),
              y: Number(region.y),
              w: Number(region.w),
              h: Number(region.h),
              rotation: Number(
                region.rotation ?? 0
              )
            };
          }
        );

        if (isMounted) {
          setMapRegions(validData);
          setMapError("");
        }
      } catch (error) {
        console.error(
          "Failed to load map coordinates:",
          error
        );

        if (isMounted) {
          setMapError(error.message);
          setMapRegions([]);
        }
      }
    }

    loadMapCoordinates();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!apiWbc.length) return;

    const rows = apiWbc.filter(
      x =>
        String(x.region).toUpperCase() ===
        String(myLocation).toUpperCase()
    );

    if (rows.length) {
      setTrendData(
        rows
          .slice()
          .sort(
            (a, b) => a.bulan_ke - b.bulan_ke
          )
          .map(x => ({
            day: x.bulan,
            value: Number(
              x.luas_terkena_ha || 0
            )
          }))
      );
    }
  }, [myLocation, apiWbc]);

  useEffect(() => {
    if (!apiWbc.length) return;

    const rows = apiWbc.filter(
      x =>
        String(x.region).toUpperCase() ===
        String(predictionLocation).toUpperCase()
    );

    if (rows.length) {
      setTrendData(
        rows
          .slice()
          .sort(
            (a, b) => a.bulan_ke - b.bulan_ke
          )
          .map(x => ({
            day: x.bulan,
            value: Number(
              x.luas_terkena_ha || 0
            )
          }))
      );
    }
  }, [predictionLocation, apiWbc]);

  const current = useMemo(
    () => getMapRisk(myLocation, riskData),
    [myLocation, riskData]
  );

  const isSafe =
  current.hasData &&
  Number(current.value || 0) === 0 &&
  Number(current.puso || 0) === 0;

const needleAngle = !current.hasData
  ? 0
  : isSafe
    ? -90
    : -90 + Math.max(
        0,
        Math.min(1, Number(current.score || 0))
      ) * 180;

  const prediction = useMemo(
    () => getMapRisk(predictionLocation, riskData),
    [predictionLocation, riskData]
  );

  // NOTIFIKASI KHUSUS WILAYAH SAYA
  const localNotifications = useMemo(() => {
    if (!current.hasData) return [];

    const items = [];

    if (Number(current.value || 0) > 0) {
      items.push({
        id: "serangan",
        title: "BPH infestation reported",
        message: `Affected area recorded: ${fmt(
          current.value
        )} ha di ${myLocation}.`
      });
    }

    if (Number(current.puso || 0) > 0) {
      items.push({
        id: "puso",
        title: "Crop failure reported",
        message: `Crop failure area recorded: ${fmt(
          current.puso
        )} ha di ${myLocation}.`
      });
    }

    return items;
  }, [current, myLocation]);

  // REKOMENDASI OTOMATIS BERDASARKAN NOTIFIKASI
  const localRecommendations = useMemo(() => {
    if (
      !current.hasData ||
      localNotifications.length === 0
    ) {
      return [];
    }

    const items = [];

    if (Number(current.value || 0) > 0) {
      items.push(
        "Inspect rice plants directly and record the BPH population."
      );

      items.push(
        "Coordinate field observations with local plant pest and disease officers."
      );
    }

    if (Number(current.puso || 0) > 0) {
      items.push(
        "Inspect affected areas and document the extent of crop damage."
      );
    }

    items.push(
      "Select control measures based on field observations and the economic threshold."
    );

    return items;
  }, [current, localNotifications]);

  useEffect(() => {
    setToastVisible(true);
  }, [myLocation]);

  const titleDate = date => {
    if (!date) return "-";

    return new Date(
      `${date}T00:00:00`
    ).toLocaleDateString(
      "en-US",
      {
        day: "numeric",
        month: "short",
        year: "numeric"
      }
    );
  };

const handlePrediction = async () => {
  if (!startDate || !endDate) {
    alert("Please select both a start date and an end date.");
    return;
  }

  if (endDate < startDate) {
    alert("The end date cannot be earlier than the start date.");
    return;
  }

  setPredicted(false);

  try {
    const response = await fetch(
      `/api/wbc/predict?region=${encodeURIComponent(predictionLocation)}&start_date=${startDate}&end_date=${endDate}`
    );

    if (!response.ok) {
      throw new Error("Failed to retrieve the prediction from the backend.");
    }

    const result = await response.json();

    setPredictionResult(result);
    setPredicted(true);

  } catch (error) {
    console.error("Prediction error:", error);
    alert(
      "The prediction could not be generated. Check the backend prediction endpoint."
    );
  }
};

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            <Sprout size={29} />
          </div>

          <div>
            <b>
              PestCycle <em>AI</em>
            </b>

            <small>
              Early Warning & BPH Forecasting System
            </small>
          </div>
        </div>

        <div className="top-tagline">
          Early Warning
          <i />
          Population Forecast
          <i />
          Mitigation Recommendations
        </div>

        <div className="top-actions">
          <div className="notification-wrap">
            <button
              className="icon-button bell-button"
              onClick={() =>
                setNotificationOpen(!notificationOpen)
              }
              aria-label="Open notifications"
            >
              <Bell size={20} />

              {localNotifications.length > 0 && (
                <span className="notification-count">
                  {localNotifications.length}
                </span>
              )}
            </button>

            {notificationOpen && (
              <div className="notification-popover">
                <strong>
                  Latest Notifications
                </strong>

                {localNotifications.length === 0 ? (
                  <p>
                    <b>{myLocation}</b>: the region is currently safe based on the latest available data.
                  </p>
                ) : (
                  localNotifications.map(item => (
                    <p key={item.id}>
                      <b>{item.title}</b>
                      <br />
                      {item.message}
                    </p>
                  ))
                )}
              </div>
            )}
          </div>

          <div
            className="auto-location-label"
            title={locationStatus}
          >
            <MapPin size={17} />
            <span>{myLocation}</span>
          </div>
        </div>
      </header>

      <section
        className="live-datetime"
        aria-label="Date and time in Western Indonesia Time"
      >
        <div className="live-date">
          <CalendarDays size={17} />

          <span>
            {clockNow.toLocaleDateString(
              "en-US",
              {
                timeZone: "Asia/Jakarta",
                weekday: "long",
                day: "numeric",
                month: "long",
                year: "numeric"
              }
            )}
          </span>
        </div>
        <div className="live-clock">
          <span className="clock-dot" />

          <strong>
            {clockNow.toLocaleTimeString(
              "en-US",
              {
                timeZone: "Asia/Jakarta",
                hour: "2-digit",
                minute: "2-digit",
                second: "2-digit",
                hour12: false
              }
            )}
          </strong>

          <small>WIB · Indonesia</small>
        </div>
      </section>

      {toastVisible && localNotifications.length > 0 && (
        <NotificationToast
          location={myLocation}
          notifications={localNotifications}
          onClose={() => setToastVisible(false)}
        />
      )}

      <div className="location-status-line">
        <MapPin size={13} />
        {locationStatus}
      </div>

      <nav className="feature-tabs">
        <button
          className={
            tab === "mine"
              ? "feature-tab active"
              : "feature-tab"
          }
          onClick={() => setTab("mine")}
        >
          <MapPin size={21} />

          <span>
            <b>Wilayah Saya</b>

            <small>
              Pantau kondisi WBC di lokasi Anda
            </small>
          </span>
        </button>

        <button
          className={
            tab === "prediction"
              ? "feature-tab active"
              : "feature-tab"
          }
          onClick={() => setTab("prediction")}
        >
          <CalendarDays size={21} />

          <span>
            <b>Prediksi WBC</b>

            <small>
              Prediksi untuk wilayah dan tanggal pilihan
            </small>
          </span>
        </button>
      </nav>

      {apiError && (
        <div
          className="panel"
          style={{
            margin: "12px 0",
            padding: 14,
            color: "#9a3412",
            background: "#fff7ed"
          }}
        >
          <strong>Backend belum tersambung</strong>

          <p>{apiError}</p>

          <small>
            Jalankan backend melalui backend\run_api.bat
            dan biarkan jendela server tetap terbuka.
          </small>
        </div>
      )}

      {apiReady && (
        <div
          className="data-status"
          style={{
            margin: "8px 0",
            color: "#28734a",
            fontSize: 12
          }}
        >
          ● Data connected · NASA POWER{" "}
          {apiWeather?.date || ""} · SiPerDitTan 2026 ·
          38 regencies/cities
        </div>
      )}

      {mapError && (
        <div
          className="panel"
          style={{
            margin: "12px 0",
            padding: 14,
            color: "#b42318",
            background: "#fff1f0"
          }}
        >
          <strong>
            Failed to load map coordinates
          </strong>

          <p>{mapError}</p>

          <small>
            Make sure the JSON file is in the public folder.
          </small>
        </div>
      )}

      {tab === "mine" ? (
        <main className="dashboard">

          <section className="welcome-banner">
            <div>
              <h1>
                Hello, {myLocation} Farmer!
              </h1>

              <p>
                Here is the latest information on Brown Planthopper
                 (BPH) activity in your region.
              </p>
            </div>
          </section>

          <section className="metric-grid">

            <Metric
              icon={Thermometer}
              label="Temperature"
              value={
                apiWeather?.values?.T2M != null
                  ? `${fmt(apiWeather.values.T2M)} °C`
                  : "—"
              }
              note={
                apiWeather
                  ? `NASA POWER · ${apiWeather.date}`
                  : "Awaiting NASA POWER data"
              }
              tone="red"
            />

            <Metric
              icon={Droplets}
              label="Humidity"
              value={
                apiWeather?.values?.RH2M != null
                  ? `${fmt(apiWeather.values.RH2M)} %`
                  : "—"
              }
              note="NASA POWER"
              tone="blue"
            />

            <Metric
              icon={CloudRain}
              label="Rainfall"
              value={
                apiWeather?.values?.PRECTOTCORR != null
                  ? `${fmt(apiWeather.values.PRECTOTCORR)} mm`
                  : "—"
              }
              note="NASA POWER"
              tone="blue"
            />

            <Metric
              icon={Bug}
              label="BPH Population Estimate"
              value={
                current.value === null
                  ? "Not available"
                  : `${current.value} individuals/m²`
              }
              note={
                current.value === null
                  ? "Data unavailable"
                  : "Observasi SiPerDitTan"
              }
              tone="orange"
            />

          </section>

          <section className="mine-grid">

            <article className="panel map-panel">

              <div className="panel-heading">
                <h2>
                  <Map size={18} />
                  Peta Risiko WBC Jawa Timur
                </h2>

                <span className="subtle-tag">
                  {mapRegions.length} wilayah
                </span>
              </div>

              <EastJavaMap
                selected={myLocation}
                onSelect={location => {
                  setMyLocation(location);
                  setToastVisible(true);
                }}
                mapRegions={mapRegions}
                riskData={riskData}
              />

              <div className="map-legend">
                {Object.entries(riskColors)
                  .filter(
                    ([label]) =>
                      label !== "No data"
                  )
                  .map(([label, color]) => (
                    <span key={label}>
                      <i
                        style={{
                          background: color
                        }}
                      />
                      {label}
                    </span>
                  ))}
              </div>

            </article>

            <article className="panel chart-panel">

              <div className="panel-heading">
                <h2>
                  <TrendingUp size={18} />
                  BPH Population Trend – {myLocation}
                </h2>

                <span className="subtle-tag">
                  Historical BPH Records
                </span>
              </div>

              <div className="chart-box">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <AreaChart data={trendData}>

                    <defs>
                      <linearGradient
                        id="mineFill"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="0%"
                          stopColor="#e84b4b"
                          stopOpacity={0.26}
                        />

                        <stop
                          offset="100%"
                          stopColor="#e84b4b"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>

                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#e7eee8"
                    />

                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 11 }}
                    />

                    <YAxis
                      tick={{ fontSize: 11 }}
                    />

                    <Tooltip />

                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#e24b4b"
                      strokeWidth={3}
                      fill="url(#mineFill)"
                    />

                  </AreaChart>
                </ResponsiveContainer>

              </div>

            </article>

            <article className="panel risk-panel">

              <div className="panel-heading">
                <h2>
                  <ShieldAlert size={18} />
                  Tingkat Risiko
                </h2>
              </div>

<div className="risk-gauge">
  <div className="gauge-arc" />

  <div
    className="gauge-needle"
    style={{
      transform: `rotate(${needleAngle}deg)`,
      backgroundColor: isSafe ? "#22a65a" : current.color
    }}
  />
</div>

              <strong
                className="risk-word"
                style={{
                  color: current.color
                }}
              >
                {current.label}
              </strong>

              <p>
                {!current.hasData
                  ? "Regional data is not available."
                  : localNotifications.length === 0
                    ? "The region is currently safe. No BPH infestation was reported in the latest available data."
                    : "An infestation has been reported. Conduct field monitoring and follow up based on local conditions."}
              </p>

            </article>

          </section>

          <section className="bottom-grid">

            <article className="panel">

              <div className="panel-heading">
                <h2>
                  <Activity size={18} />
                  Wilayah dengan Risiko Tertinggi
                </h2>
              </div>

              <div className="risk-bars">

                {riskData
                  .slice()
                  .sort((a, b) => b.score - a.score)
                  .map(region => (
                    <div
                      className="risk-bar-row"
                      key={region.name}
                    >
                      <span>
                        {region.name}
                      </span>

                      <div>
                        <i
                          style={{
                            width: `${region.score * 100}%`,
                            background: region.color
                          }}
                        />
                      </div>

                      <b>
                        {region.score.toFixed(2)}
                      </b>
                    </div>
                  ))}

              </div>

            </article>

            <article className="panel recommendation-panel">

              <div className="panel-heading">
                <h2>
                  <Leaf size={18} />
                  Mitigation Recommendations
                </h2>
              </div>
                            {!current.hasData ? (
                <p>
                  <Info size={17} />
                  Data wilayah belum tersedia untuk menyusun rekomendasi.
                </p>
              ) : localRecommendations.length === 0 ? (
                <p>
                  <CheckCircle2 size={17} />
                  Wilayah aman. Tidak ada rekomendasi penanganan khusus saat ini.
                </p>
              ) : (
                localRecommendations.map((text, index) => (
                  <p key={index}>
                    <CheckCircle2 size={17} />
                    {text}
                  </p>
                ))
              )}

            </article>

          </section>

        </main>
      ) : (
        <>
          <main className="dashboard">

            <section className="prediction-title">

              <div>
                <span className="eyebrow">
                  REGION- AND TIME-BASED ANALYSIS
                </span>

                <h1>
                  Population Forecast WBC
                </h1>

                <p>
                  Explore population projections and risk levels for
                  Wereng Batang Cokelat di 38 regencies/cities
                  East Java.
                </p>
              </div>

              <div className="title-icon">
                <CalendarDays size={34} />
              </div>

            </section>

            <section className="prediction-controls panel">

              <label>
                <span>
                  <MapPin size={16} />
                  Pilih Wilayah
                </span>

                <select
                  value={predictionLocation}
                  onChange={event => {
                    setPredictionLocation(event.target.value);
                    setPredicted(false);
                  }}
                >
                  {locations.map(location => (
                    <option
                      key={location}
                      value={location}
                    >
                      {location}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span>
                  <CalendarDays size={16} />
                  Tanggal Mulai
                </span>

                <input
                  type="date"
                  value={startDate}
                  onChange={event => {
                    setStartDate(event.target.value);
                    setPredicted(false);
                  }}
                />
              </label>

              <label>
                <span>
                  <CalendarDays size={16} />
                  Tanggal Akhir
                </span>

                <input
                  type="date"
                  value={endDate}
                  min={startDate}
                  onChange={event => {
                    setEndDate(event.target.value);
                    setPredicted(false);
                  }}
                />
              </label>

              <button
                className="primary-button"
                onClick={handlePrediction}
              >
                <Activity size={17} />
                Tampilkan Prediksi
                <ChevronRight size={17} />
              </button>

            </section>

            <section className="prediction-map-row">

              <article className="panel prediction-map-panel">

                <div className="panel-heading">
                  <h2>
                    <Map size={18} />
                    Peta Prediksi Risiko WBC – Jawa Timur
                  </h2>

                  <span className="subtle-tag">
                    {mapRegions.length} wilayah
                  </span>
                </div>

                <EastJavaMap
                  selected={predictionLocation}
                  onSelect={location => {
                    setPredictionLocation(location);
                    setPredicted(false);
                  }}
                  mapRegions={mapRegions}
                  riskData={riskData}
                  large
                />

                <div className="map-legend">
                  {Object.entries(riskColors)
                    .filter(
                      ([label]) =>
                        label !== "No data"
                    )
                    .map(([label, color]) => (
                      <span key={label}>
                        <i
                          style={{ background: color }}
                        />
                        {label}
                      </span>
                    ))}
                </div>

              </article>

              <article className="panel prediction-summary">

                <div className="panel-heading">
                  <h2>
                    <Activity size={18} />
                    Hasil Prediksi – {predictionLocation}
                  </h2>
                </div>

                <div className="summary-number">
                  <span>
                    Affected Area in the Latest Available Record
                  </span>

                  <strong>
                    {prediction.value === null
                      ? "Not available"
                      : `${fmt(prediction.value)} ha`}
                  </strong>
                </div>

                <div className="summary-row">
                  <span>
                    <CalendarDays size={16} />
                    Periode
                  </span>

                  <b>
                    {titleDate(startDate)} – {titleDate(endDate)}
                  </b>
                </div>

                <div className="summary-row">
                  <span>
                    <ShieldAlert size={16} />
                    Indikator risiko
                  </span>

                  <b style={{ color: prediction.color }}>
                    {prediction.label}
                  </b>
                </div>

                <div className="summary-note">
                  <Info size={15} />

                  {predicted
                    ? prediction.value === null
                      ? "No historical records are available for this region."
                      : "Regional analysis and BPH indicators for the selected period."
                    : "Select a region and date range, then generate the forecast."}
                </div>

              </article>

            </section>

            <section className="prediction-charts">

              <article className="panel">

                <div className="panel-heading">
                  <h2>
                    <TrendingUp size={18} />
                    Historical BPH Affected Area – {predictionLocation}
                  </h2>

                  <span className="subtle-tag">
                    Historical BPH Records
                  </span>
                </div>

                <div className="chart-box tall">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <AreaChart data={trendData}>

                      <defs>
                        <linearGradient
                          id="predFill"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#f28a24"
                            stopOpacity={0.28}
                          />

                          <stop
                            offset="100%"
                            stopColor="#f28a24"
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>

                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#e7eee8"
                      />

                      <XAxis
                        dataKey="day"
                        tick={{ fontSize: 11 }}
                      />

                      <YAxis
                        tick={{ fontSize: 11 }}
                      />

                      <Tooltip />

                      <Area
                        type="monotone"
                        dataKey="value"
                        stroke="#f28a24"
                        strokeWidth={3}
                        fill="url(#predFill)"
                      />

                    </AreaChart>
                  </ResponsiveContainer>

                </div>

              </article>

              <article className="panel">

                <div className="panel-heading">
                  <h2>
                    <Map size={18} />
                    Perbandingan Antarwilayah
                  </h2>
                </div>

                <div className="comparison-bars">

                  {riskData
                    .slice()
                    .sort((a, b) => b.value - a.value)
                    .map(region => (
                      <div
                        className="comparison-row"
                        key={region.name}
                      >
                        <span>
                          {region.name}
                        </span>

                        <div>
                          <i
                            style={{
                              width: `${(region.value / 550) * 100}%`,
                              background: region.color
                            }}
                          />
                        </div>

                        <b>
                          {region.value}
                        </b>
                      </div>
                    ))}

                </div>

              </article>

              <article className="panel recommendation-panel">

                <div className="panel-heading">
                  <h2>
                    <Leaf size={18} />
                    Rekomendasi Antisipasi
                  </h2>
                </div>

                {!prediction.hasData ? (
                  <p>
                    <Info size={17} />
                    Data untuk wilayah ini belum tersedia.
                  </p>
                ) : Number(prediction.value || 0) === 0 &&
                  Number(prediction.puso || 0) === 0 ? (
                  <p>
                    <CheckCircle2 size={17} />
                    Kondisi wilayah aman berdasarkan data terbaru.
                    Tidak diperlukan rekomendasi penanganan khusus.
                  </p>
                ) : (
                  <>
                    <p>
                      <CheckCircle2 size={17} />
                      Tingkatkan pemantauan populasi WBC di area terpilih.
                    </p>

                    <p>
                      <CheckCircle2 size={17} />
                      Catat stadia WBC dan keberadaan musuh alami.
                    </p>

                    <p>
                      <CheckCircle2 size={17} />
                      Lakukan pengendalian berdasarkan hasil pengamatan
                      dan ambang kendali.
                    </p>
                  </>
                )}

              </article>

            </section>

            {apiMetrics && (
              <section
                className="panel"
                style={{
                  marginTop: 18,
                  padding: 18
                }}
              >
                <div className="panel-heading">
                  <h2>
                    <Activity size={18} />
                    Evaluasi Awal Model AI
                  </h2>

                  <span className="subtle-tag">
                    Evaluasi model
                  </span>
                </div>

                <p
                  style={{
                    color: "#64748b",
                    fontSize: 13
                  }}
                >
                  The following metrics are based on initial testing of the
                  2026 dataset and do not yet represent
                  multi-year temporal validation.
                </p>

                {(apiMetrics.classification || []).map(
                  (metric, index) => (
                    <div
                      key={`${metric.MODEL || metric.model || "model"}-${index}`}
                      className="summary-row"
                    >
                      <span>
                        {metric.MODEL ||
                          metric.model ||
                          "Classification Model"}
                      </span>

                      <b>
                        F1: {fmt(metric.F1 ?? metric.f1, 3)}
                        {" · "}
                        PR-AUC: {fmt(
                          metric.PR_AUC ?? metric.pr_auc,
                          3
                        )}
                      </b>
                    </div>
                  )
                )}

              </section>
            )}

          </main>
        </>
      )}

      <footer className="footer">
        <span>
          © 2026 PestCycle AI
        </span>

        <span>
          Sistem Early Warning & Prediksi Wereng Batang
          · East Java
        </span>
      </footer>

    </div>
  );
}