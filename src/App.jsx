
import React, {
  useCallback,
  useEffect,
  useMemo,
  useState
} from "react";

import {
  Bell,
  MapPin,
  CalendarDays,
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
  Info,
  RefreshCw,
  AlertTriangle,
  Database,
  ChevronRight
} from "lucide-react";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar
} from "recharts";

// ======================================================
// 1. CONFIGURATION
// ======================================================

const API = "/api";
const MAP_JSON = "/koordinat-peta-jawa-timur.json";

const MAP_WIDTH = 1200;
const MAP_HEIGHT = 760;

const RISK_COLORS = {
  low: "#28a66a",
  moderate: "#e7bd35",
  high: "#ed8a32",
  critical: "#df4545",
  nodata: "#a4b1aa"
};

const INITIAL_LOCATION = "Malang";

const now = new Date();

const INITIAL_START_DATE =
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;

const INITIAL_END_DATE =
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()).padStart(2, "0")}`;

const fmt = (value, digits = 2) => {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    !Number.isFinite(Number(value))
  ) {
    return "—";
  }

  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: digits
  });
};

const formatDate = (value) => {
  if (!value) return "—";

  const date = new Date(`${value}T00:00:00`);

  if (Number.isNaN(date.getTime())) return value;

  return date.toLocaleDateString("en-US", {
    day: "numeric",
    month: "short",
    year: "numeric"
  });
};

const normalizeRegion = (value) =>
  String(value || "")
    .trim()
    .toUpperCase()
    .replace(/^KABUPATEN\s+/, "")
    .replace(/^KOTA\s+/, "")
    .replace(/\s+/g, " ");

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers
    }
  });

  const contentType =
    response.headers.get("content-type") || "";

  let data = null;

  if (contentType.includes("application/json")) {
    data = await response.json();
  }

  if (!response.ok) {
    throw new Error(
      data?.detail ||
      data?.message ||
      `API Error ${response.status}`
    );
  }

  return data;
}

// ======================================================
// 2. HISTORICAL WBC DATA
// ======================================================

function getLatestWbcMonth(rows = []) {
  if (!rows.length) return [];

  const latestKey = Math.max(
    ...rows.map((item) =>
      Number(item.tahun || 0) * 100 +
      Number(item.bulan_ke || 0)
    )
  );

  return rows.filter((item) => {
    const key =
      Number(item.tahun || 0) * 100 +
      Number(item.bulan_ke || 0);

    return key === latestKey;
  });
}

function getRegionHistory(rows = [], region) {
  return rows
    .filter(
      (item) =>
        normalizeRegion(item.region) ===
        normalizeRegion(region)
    )
    .slice()
    .sort(
      (a, b) =>
        Number(a.tahun) - Number(b.tahun) ||
        Number(a.bulan_ke) - Number(b.bulan_ke)
    )
    .map((item) => ({
      date: `${item.tahun}-${String(
        item.bulan_ke
      ).padStart(2, "0")}`,
      month: `${item.bulan} ${item.tahun}`,
      affected: Number(item.luas_terkena_ha || 0),
      puso: Number(item.luas_puso_ha || 0)
    }));
}

// ======================================================
// 3. RISK CLASSIFICATION
// ======================================================

function buildRiskData(mapRegions = [], rows = []) {
  const latestRows = getLatestWbcMonth(rows);

  const grouped = new globalThis.Map();

  latestRows.forEach((item) => {
    const key = normalizeRegion(item.region);
    if (!key) return;

    const previous = grouped.get(key) || {
      value: 0,
      puso: 0
    };

    previous.value += Number(item.luas_terkena_ha || 0);
    previous.puso += Number(item.luas_puso_ha || 0);

    grouped.set(key, previous);
  });

  const maxValue = Math.max(
    0,
    ...Array.from(grouped.values()).map(item => item.value)
  );

  return mapRegions.map(region => {
    const data = grouped.get(normalizeRegion(region.name));

    if (!data) {
      return {
        name: region.name,
        value: null,
        puso: null,
        score: null,
        hasData: false,
        label: "No Data",
        level: "nodata",
        color: RISK_COLORS.nodata
      };
    }

    const score = maxValue > 0
      ? data.value / maxValue
      : 0;

    let level = "low";
    let label = "No Reported Attack";
    let color = RISK_COLORS.low;

    if (data.value > 0) {
      if (score >= 0.75) {
        level = "critical";
        label = "Critical Relative Impact";
        color = RISK_COLORS.critical;
      } else if (score >= 0.50) {
        level = "high";
        label = "High Relative Impact";
        color = RISK_COLORS.high;
      } else if (score >= 0.25) {
        level = "moderate";
        label = "Moderate Relative Impact";
        color = RISK_COLORS.moderate;
      } else {
        level = "low";
        label = "Low Relative Impact";
        color = RISK_COLORS.low;
      }
    }

    return {
      name: region.name,
      value: data.value,
      puso: data.puso,
      score,
      hasData: true,
      label,
      level,
      color
    };
  });
}

function getRegionRisk(region, riskData = []) {
  const result = riskData.find(
    (item) =>
      normalizeRegion(item.name) ===
      normalizeRegion(region)
  );

  if (!result) {
    return {
      name: region,
      value: null,
      puso: null,
      score: null,
      hasData: false,
      label: "No Data",
      level: "nodata",
      color: RISK_COLORS.nodata
    };
  }

  return result;
}

// ======================================================
// 4. MAP COMPONENT
// ======================================================

function getMapStyle(region) {
  return {
    position: "absolute",
    left: `${(Number(region.x) / MAP_WIDTH) * 100}%`,
    top: `${(Number(region.y) / MAP_HEIGHT) * 100}%`,
    width: `${(Number(region.w) / MAP_WIDTH) * 100}%`,
    height: `${(Number(region.h) / MAP_HEIGHT) * 100}%`,
    transform: `rotate(${Number(region.rotation || 0)}deg)`,
    transformOrigin: "center",
    padding: 0,
    border: 0,
    margin: 0,
    background: "transparent",
    overflow: "visible"
  };
}

function EastJavaMap({
  selected,
  onSelect,
  mapRegions = [],
  riskData = [],
  large = false
}) {
  const selectedRisk = getRegionRisk(
    selected,
    riskData
  );

  return (
    <div
      className={`east-java-map image-map ${
        large ? "map-large" : ""
      }`}
      role="group"
      aria-label="Interactive East Java WBC risk map"
      style={{
        position: "relative",
        width: "100%",
        aspectRatio: `${MAP_WIDTH}/${MAP_HEIGHT}`,
        overflow: "hidden",
        background: "#ffffff",
        isolation: "isolate"
      }}
    >
      {mapRegions.length === 0 && (
        <div className="map-loading-message">
          Loading regional map...
        </div>
      )}

      {mapRegions.map((region) => {
        const risk = getRegionRisk(
          region.name,
          riskData
        );

        const isSelected =
          normalizeRegion(region.name) ===
          normalizeRegion(selected);

        const imageUrl =
          `/wilayah-jatim/${region.file}.png`;

        return (
          <button
            key={region.name}
            type="button"
            className={`map-region ${
              isSelected ? "selected" : ""
            }`}
            style={{
              ...getMapStyle(region),
              zIndex: isSelected ? 100 : 1,
              cursor: "pointer"
            }}
            onClick={() => onSelect(region.name)}
            title={`${region.name}: ${risk.label}`}
            aria-label={`${region.name}: ${risk.label}`}
            aria-pressed={isSelected}
          >
            <span
              aria-hidden="true"
              style={{
                display: "block",
                width: "100%",
                height: "calc(100% - 17px)",

                backgroundColor: risk.color,

                WebkitMaskImage: `url("${imageUrl}")`,
                maskImage: `url("${imageUrl}")`,

                WebkitMaskRepeat: "no-repeat",
                maskRepeat: "no-repeat",

                WebkitMaskPosition: "center",
                maskPosition: "center",

                WebkitMaskSize: "contain",
                maskSize: "contain",

                opacity: risk.hasData ? 1 : 0.65,

                transition:
                  "background-color 0.3s ease, opacity 0.3s ease"
              }}
            />

            

{/* ORIGINAL MAP IMAGE WITH WHITE LABELS */}
<img
  src={imageUrl}
  alt={region.name}
  draggable={false}
  style={{
    position: "absolute",
    inset: 0,
    width: "100%",
    height: "100%",
    objectFit: "contain",
    pointerEvents: "none",
    userSelect: "none",
    zIndex: 1
  }}
/>

{/* DYNAMIC RISK COLOR OVERLAY */}
<span
  aria-hidden="true"
  style={{
    position: "absolute",
    inset: 0,
    backgroundColor: risk.color,

    WebkitMaskImage: `url("${imageUrl}")`,
    maskImage: `url("${imageUrl}")`,

    WebkitMaskRepeat: "no-repeat",
    maskRepeat: "no-repeat",

    WebkitMaskPosition: "center",
    maskPosition: "center",

    WebkitMaskSize: "contain",
    maskSize: "contain",

    mixBlendMode: "hue",
    pointerEvents: "none",
    zIndex: 2,
    opacity: risk.hasData ? 1 : 0.65
  }}
/>


          </button>
        );
      })}

      <div
        className="map-selected-info"
        aria-live="polite"
      >
        <strong>
          {selected || "Select a region"}
        </strong>

        <span style={{ color: selectedRisk.color }}>
          ● {selectedRisk.label}
        </span>

        {selectedRisk.value !== null && (
          <small>
            Affected Area: {fmt(selectedRisk.value)} ha
          </small>
        )}

        {!selectedRisk.hasData && (
          <small>
            Regional data is not available.
          </small>
        )}
      </div>
    </div>
  );
}

// ======================================================
// 5. METRIC COMPONENT
// ======================================================

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

// ======================================================
// 6. NOTIFICATION COMPONENT
// ======================================================

function NotificationToast({
  location,
  notifications,
  onClose
}) {
  if (!notifications.length) return null;

  return (
    <div className="toast">
      <div className="toast-icon">
        <Bell size={19} />
      </div>

      <div className="toast-copy">
        <strong>WBC Alert · {location}</strong>
        <span>{notifications[0].message}</span>
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

// ======================================================
// 7. MAIN APPLICATION
// ======================================================

export default function App() {

  // ----------------------------------------------------
  // A. MAIN STATES
  // ----------------------------------------------------

  const [tab, setTab] = useState("mine");

  const [clockNow, setClockNow] = useState(
    () => new Date()
  );

  const [myLocation, setMyLocation] = useState(
    INITIAL_LOCATION
  );

  const [predictionLocation, setPredictionLocation] =
    useState("Banyuwangi");

  const [startDate, setStartDate] = useState(
    INITIAL_START_DATE
  );

  const [endDate, setEndDate] = useState(
    INITIAL_END_DATE
  );

  // ----------------------------------------------------
  // B. BACKEND STATES
  // ----------------------------------------------------

  const [apiReady, setApiReady] = useState(false);
  const [apiLoading, setApiLoading] = useState(true);
  const [apiError, setApiError] = useState("");

  const [apiHealth, setApiHealth] = useState(null);
  const [apiWeather, setApiWeather] = useState(null);

  const [weatherLoading, setWeatherLoading] =
    useState(false);

  const [weatherError, setWeatherError] = useState("");

  const [apiWbc, setApiWbc] = useState([]);
  const [apiMonthly, setApiMonthly] = useState([]);
  const [apiMetrics, setApiMetrics] = useState(null);

  // ----------------------------------------------------
  // C. MAP STATES
  // ----------------------------------------------------

  const [mapRegions, setMapRegions] = useState([]);
  const [mapLoading, setMapLoading] = useState(true);
  const [mapError, setMapError] = useState("");

  // ----------------------------------------------------
  // D. PREDICTION STATES
  // ----------------------------------------------------

  const [predictionResult, setPredictionResult] =
    useState(null);

  const [predictionLoading, setPredictionLoading] =
    useState(false);

  const [predictionError, setPredictionError] =
    useState("");

  const [predicted, setPredicted] = useState(false);

  // ----------------------------------------------------
  // E. NOTIFICATION STATES
  // ----------------------------------------------------

  const [notificationOpen, setNotificationOpen] =
    useState(false);

  const [toastVisible, setToastVisible] =
    useState(false);

  // ----------------------------------------------------
  // F. DERIVED DATA
  // ----------------------------------------------------

  const locations = useMemo(
    () => mapRegions.map((region) => region.name),
    [mapRegions]
  );

  const riskData = useMemo(
    () => buildRiskData(mapRegions, apiWbc),
    [mapRegions, apiWbc]
  );

  const current = useMemo(
    () => getRegionRisk(myLocation, riskData),
    [myLocation, riskData]
  );

  const mineTrend = useMemo(
    () => getRegionHistory(apiWbc, myLocation),
    [apiWbc, myLocation]
  );

  const predictionHistory = useMemo(
    () => getRegionHistory(apiWbc, predictionLocation),
    [apiWbc, predictionLocation]
  );

  const latestWbcDate = useMemo(() => {
    if (!apiWbc.length) return "—";

    const latest = getLatestWbcMonth(apiWbc);

    if (!latest.length) return "—";

    return `${latest[0].bulan} ${latest[0].tahun}`;
  }, [apiWbc]);

  const weatherValues = apiWeather?.values || {};

  // ----------------------------------------------------
  // 8. REAL-TIME CLOCK
  // ----------------------------------------------------

  useEffect(() => {
    const timer = window.setInterval(() => {
      setClockNow(new Date());
    }, 1000);

    return () => window.clearInterval(timer);
  }, []);

  // ----------------------------------------------------
  // 9. LOAD EAST JAVA MAP DATA
  // ----------------------------------------------------

  useEffect(() => {
    let active = true;

    async function loadMap() {
      setMapLoading(true);

      try {
        const response = await fetch(
          `${MAP_JSON}?v=3`
        );

        if (!response.ok) {
          throw new Error(
            "Regional map coordinate file could not be found."
          );
        }

        const data = await response.json();

        if (
          !Array.isArray(data) ||
          data.length !== 38
        ) {
          throw new Error(
            "The map must contain exactly 38 regions."
          );
        }

        const valid = data.map((region, index) => {
          const validRegion =
            region &&
            typeof region.name === "string" &&
            typeof region.file === "string" &&
            ["x", "y", "w", "h"].every(
              (key) =>
                Number.isFinite(Number(region[key]))
            ) &&
            Number(region.w) > 0 &&
            Number(region.h) > 0;

          if (!validRegion) {
            throw new Error(
              `Invalid map coordinates for region ${index + 1}.`
            );
          }

          return {
            ...region,
            x: Number(region.x),
            y: Number(region.y),
            w: Number(region.w),
            h: Number(region.h),
            rotation: Number(region.rotation || 0)
          };
        });

        if (active) {
          setMapRegions(valid);
          setMapError("");
        }

      } catch (error) {
        if (active) {
          setMapError(error.message);
          setMapRegions([]);
        }

      } finally {
        if (active) {
          setMapLoading(false);
        }
      }
    }

    loadMap();

    return () => {
      active = false;
    };
  }, []);

  // ----------------------------------------------------
  // 10. LOAD MAIN BACKEND DATA
  // ----------------------------------------------------

  const loadDashboardData = useCallback(
    async (signal) => {
      setApiLoading(true);
      setApiError("");

      try {
        const [
          health,
          wbcData,
          monthlyData,
          metrics
        ] = await Promise.all([
          apiFetch("/health", { signal }),
          apiFetch("/wbc/2026", { signal }),
          apiFetch("/wbc/summary/monthly", { signal }),
          apiFetch("/model/metrics", { signal })
        ]);

        if (signal.aborted) return;

        if (!Array.isArray(wbcData.items)) {
          throw new Error(
            "Invalid WBC data format returned by the backend."
          );
        }

        setApiHealth(health);
        setApiWbc(wbcData.items);
        setApiMonthly(monthlyData.items || []);
        setApiMetrics(metrics);

        setApiReady(true);
        setApiError("");

      } catch (error) {
        if (signal.aborted) return;

        setApiReady(false);
        setApiError(error.message);

      } finally {
        if (!signal.aborted) {
          setApiLoading(false);
        }
      }
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();

    loadDashboardData(controller.signal);

    return () => controller.abort();
  }, [loadDashboardData]);

  // ----------------------------------------------------
  // 11. REGIONAL WEATHER
  // ----------------------------------------------------

  useEffect(() => {
    if (!myLocation) return;

    const controller = new AbortController();

    async function loadRegionalWeather() {
      setWeatherLoading(true);
      setWeatherError("");
      setApiWeather(null);

      try {
        const region = encodeURIComponent(myLocation);

        const result = await apiFetch(
          `/weather/latest?region=${region}`,
          { signal: controller.signal }
        );

        if (!controller.signal.aborted) {
          setApiWeather(result);
        }

      } catch (error) {
        if (!controller.signal.aborted) {
          setApiWeather(null);
          setWeatherError(error.message);
        }

      } finally {
        if (!controller.signal.aborted) {
          setWeatherLoading(false);
        }
      }
    }

    loadRegionalWeather();

    return () => controller.abort();
  }, [myLocation]);

  // ----------------------------------------------------
  // 12. DEFAULT REGION VALIDATION
  // ----------------------------------------------------

  useEffect(() => {
    if (!locations.length) return;

    const selectedExists = locations.some(
      (name) =>
        normalizeRegion(name) ===
        normalizeRegion(myLocation)
    );

    if (!selectedExists) {
      setMyLocation(locations[0]);
    }

    const predictionExists = locations.some(
      (name) =>
        normalizeRegion(name) ===
        normalizeRegion(predictionLocation)
    );

    if (!predictionExists) {
      setPredictionLocation(locations[0]);
    }
  }, [
    locations,
    myLocation,
    predictionLocation
  ]);

  // ----------------------------------------------------
  // 13. DATA-BASED NOTIFICATIONS
  // ----------------------------------------------------

  const localNotifications = useMemo(() => {
    if (!current.hasData) {
      return [{
        id: "no-data",
        title: "Regional Data Unavailable",
        message:
          `No recent WBC observation data is available for ${myLocation}. Field monitoring is recommended.`,
        type: "info"
      }];
    }

    const notifications = [];

    if (Number(current.value || 0) > 0) {
      notifications.push({
        id: "affected-area",
        title: "Reported WBC Attack",
        message:
          `A reported affected area of ${fmt(
            current.value
          )} ha has been recorded in ${myLocation}.`,
        type: "warning"
      });
    }

    if (Number(current.puso || 0) > 0) {
      notifications.push({
        id: "puso-area",
        title: "Reported Crop Failure",
        message:
          `A crop failure area of ${fmt(
            current.puso
          )} ha has been recorded in ${myLocation}.`,
        type: "critical"
      });
    }

    if (notifications.length === 0) {
      notifications.push({
        id: "no-reported-attack",
        title: "No Reported Attack",
        message:
          `No affected area was recorded in the latest available WBC data for ${myLocation}. This does not confirm that the region is pest-free.`,
        type: "safe"
      });
    }

    return notifications;
  }, [current, myLocation]);

  // ----------------------------------------------------
  // 14. MITIGATION RECOMMENDATIONS
  // ----------------------------------------------------

  const localRecommendations = useMemo(() => {
    if (!current.hasData) {
      return [
        "Regional WBC data is unavailable. Do not classify the region as safe.",
        "Conduct field observations and coordinate with local plant protection officers.",
        "Collect and report updated WBC population observations."
      ];
    }

    const recommendations = [];

    if (Number(current.value || 0) > 0) {
      recommendations.push(
        "Conduct direct field observations in rice fields with reported WBC attacks."
      );

      recommendations.push(
        "Record WBC population by nymph and adult development stages."
      );

      recommendations.push(
        "Monitor natural enemies before deciding on pest control measures."
      );
    }

    if (Number(current.puso || 0) > 0) {
      recommendations.push(
        "Map and document crop failure areas for damage assessment."
      );
    }

    if (
      Number(current.value || 0) === 0 &&
      Number(current.puso || 0) === 0
    ) {
      recommendations.push(
        "Maintain routine monitoring of WBC populations."
      );

      recommendations.push(
        "No affected area was recorded in the latest available dataset. Continue field observations."
      );
    }

    recommendations.push(
      "Select control measures based on field observations, applicable economic thresholds, and guidance from plant protection officers."
    );

    return recommendations;
  }, [current]);

  // ----------------------------------------------------
  // 15. TOAST NOTIFICATION
  // ----------------------------------------------------

  useEffect(() => {
    setToastVisible(true);
  }, [myLocation]);

  // ----------------------------------------------------
  // 16. REGION SELECTION
  // ----------------------------------------------------

  const handleMyLocationChange = (location) => {
    setMyLocation(location);
    setToastVisible(true);
  };

  const handlePredictionLocationChange = (location) => {
    setPredictionLocation(location);

    setPredictionResult(null);
    setPredictionError("");
    setPredicted(false);
  };

  // ----------------------------------------------------
  // 17. AI PREDICTION
  // ----------------------------------------------------

  const handlePrediction = async () => {
    if (!predictionLocation) {
      setPredictionError(
        "Please select a region."
      );
      return;
    }

    if (!startDate || !endDate) {
      setPredictionError(
        "Both start and end dates are required."
      );
      return;
    }

    if (startDate > endDate) {
      setPredictionError(
        "The start date cannot be later than the end date."
      );
      return;
    }

    setPredictionLoading(true);
    setPredictionError("");
    setPredictionResult(null);
    setPredicted(false);

    try {
      const params = new URLSearchParams({
        region: predictionLocation,
        start_date: startDate,
        end_date: endDate
      });

      const result = await apiFetch(
        `/wbc/predict?${params.toString()}`
      );

      if (
        result.success !== true ||
        !Array.isArray(result.items)
      ) {
        throw new Error(
          "Invalid prediction response returned by the backend."
        );
      }

      setPredictionResult(result);
      setPredicted(true);

    } catch (error) {
      setPredictionError(error.message);

      console.error(
        "WBC prediction failed:",
        error
      );

    } finally {
      setPredictionLoading(false);
    }
  };

  // ----------------------------------------------------
  // 18. PREDICTION RESULTS
  // ----------------------------------------------------

  const predictionItems = useMemo(() => {
    if (!predictionResult?.items) return [];

    return predictionResult.items.map((item) => ({
      ...item,

      predicted_affected_ha: Number(
        item.predicted_affected_ha || 0
      ),

      probability: Math.max(
        0,
        Math.min(1, Number(item.probability || 0))
      ),

      label: item.date || "—"
    }));
  }, [predictionResult]);

  const predictionSummary = useMemo(() => {
    if (!predictionItems.length) {
      return {
        totalArea: null,
        averageProbability: null,
        highestProbability: null,
        potentialPeriods: 0
      };
    }

    const probabilities = predictionItems.map(
      (item) => item.probability
    );

    return {
      totalArea: predictionItems.reduce(
        (sum, item) =>
          sum + item.predicted_affected_ha,
        0
      ),

      averageProbability:
        probabilities.reduce(
          (sum, value) => sum + value,
          0
        ) / probabilities.length,

      highestProbability: Math.max(
        ...probabilities
      ),

      potentialPeriods: predictionItems.filter(
        (item) => item.probability >= 0.5
      ).length
    };
  }, [predictionItems]);

  // ----------------------------------------------------
  // 19. RISK GAUGE
  // ----------------------------------------------------

  const isSafe =
    current.hasData &&
    Number(current.value || 0) === 0 &&
    Number(current.puso || 0) === 0;

  const gaugeScore = !current.hasData
    ? null
    : isSafe
      ? 0
      : Math.max(
          0,
          Math.min(1, Number(current.score || 0))
        );

  // The needle moves from the left side (-90 degrees)
  // to the right side (+90 degrees).


const needleAngle = !current.hasData
  ? 0
  : -90 + (
      Math.max(
        0,
        Math.min(1, Number(current.score || 0))
      ) * 180
    );


  const titleDate = formatDate;

  const latestRecordLabel = latestWbcDate;

  // ====================================================
  // 20. APPLICATION INTERFACE
  // ====================================================

  return (
    <div className="app-shell">

      {/* HEADER */}

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
              Early Warning & WBC Forecasting System
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
                setNotificationOpen((value) => !value)
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

                <strong>WBC Notifications</strong>

                {localNotifications.map((item) => (
                  <p key={item.id}>
                    <b>{item.title}</b>
                    <br />
                    {item.message}
                  </p>
                ))}

              </div>
            )}

          </div>

          <div className="location-select">
            <MapPin size={17} />

            <select
              value={myLocation}
              onChange={(event) =>
                handleMyLocationChange(
                  event.target.value
                )
              }
              aria-label="Select monitoring region"
            >
              {locations.map((location) => (
                <option
                  key={location}
                  value={location}
                >
                  {location}
                </option>
              ))}
            </select>
          </div>

        </div>
      </header>

      {/* REAL-TIME CLOCK */}

      <section className="live-datetime">

        <div className="live-date">
          <CalendarDays size={17} />

          <span>
            {clockNow.toLocaleDateString("en-US", {
              timeZone: "Asia/Jakarta",
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric"
            })}
          </span>
        </div>

        <div className="live-clock">
          <span className="clock-dot" />

          <strong>
            {clockNow.toLocaleTimeString("en-US", {
              timeZone: "Asia/Jakarta",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false
            })}
          </strong>

          <small>WIB · Indonesia</small>
        </div>

      </section>

      {/* NOTIFICATION TOAST */}

      {toastVisible && (
        <NotificationToast
          location={myLocation}
          notifications={localNotifications}
          onClose={() => setToastVisible(false)}
        />
      )}

      {/* LOCATION STATUS */}

      <div className="location-status-line">
        <MapPin size={13} />
        Monitoring Region: {myLocation}
      </div>

      {/* NAVIGATION */}

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
            <b>My Region</b>
            <small>
              Monitor WBC conditions in your selected region
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
            <b>WBC Prediction</b>
            <small>
              Regional and time-based prediction analysis
            </small>
          </span>
        </button>

      </nav>

      {/* BACKEND STATUS */}

      {apiError && (
        <div
          className="panel"
          style={{
            margin: "12px 0",
            padding: 16,
            color: "#9a3412",
            background: "#fff7ed"
          }}
        >
          <strong>
            <AlertTriangle size={17} />
            {" "}Backend Connection Error
          </strong>

          <p>{apiError}</p>

          <small>
            Check the FastAPI server, Vercel configuration,
            and /api endpoint connection.
          </small>
        </div>
      )}

      {apiReady && (
        <div className="data-status">
          <Database size={14} />
          {" "}Backend Connected · {apiWbc.length} WBC records
          {" "}· {apiMonthly.length} summary periods
          {" "}· Latest Data: {latestRecordLabel}
        </div>
      )}

      {apiLoading && (
        <div className="panel" style={{ padding: 14 }}>
          <RefreshCw size={16} />
          {" "}Loading data from backend...
        </div>
      )}

      {mapError && (
        <div
          className="panel"
          style={{
            margin: "12px 0",
            padding: 14,
            color: "#b42318"
          }}
        >
          <strong>Map Loading Error</strong>
          <p>{mapError}</p>
        </div>
      )}

      {/* ============================================== */}
      {/* MY REGION DASHBOARD */}
      {/* ============================================== */}

      {tab === "mine" && (

        <main className="dashboard">

          <section className="welcome-banner">
            <div>
              <h1>
                Welcome, {myLocation}!
              </h1>

              <p>
                Monitor reported Brown Planthopper attacks
                and weather conditions in your selected region.
              </p>
            </div>
          </section>

          {/* WEATHER AND WBC METRICS */}

          <section className="metric-grid">

            <Metric
              icon={Thermometer}
              label="Air Temperature"
              value={
                weatherValues.T2M != null
                  ? `${fmt(weatherValues.T2M)} °C`
                  : weatherLoading
                    ? "Loading..."
                    : "—"
              }
              note={
                apiWeather
                  ? `NASA POWER · ${apiWeather.date}`
                  : weatherError || "Weather data unavailable"
              }
              tone="red"
            />

            <Metric
              icon={Droplets}
              label="Relative Humidity"
              value={
                weatherValues.RH2M != null
                  ? `${fmt(weatherValues.RH2M)} %`
                  : "—"
              }
              note="NASA POWER · RH2M"
              tone="blue"
            />

            <Metric
              icon={CloudRain}
              label="Rainfall"
              value={
                weatherValues.PRECTOTCORR != null
                  ? `${fmt(weatherValues.PRECTOTCORR)} mm`
                  : "—"
              }
              note="NASA POWER · PRECTOTCORR"
              tone="blue"
            />

            <Metric
              icon={Bug}
              label="Reported WBC Affected Area"
              value={
                current.value !== null
                  ? `${fmt(current.value)} ha`
                  : "Unavailable"
              }
              note={
                current.hasData
                  ? "SiPerDitTan Observation"
                  : "No record in the latest available period"
              }
              tone="orange"
            />

          </section>

          {/* MAP AND HISTORICAL CHART */}

          <section className="mine-grid">

            <article className="panel map-panel">

              <div className="panel-heading">

                <h2>
                  <Map size={18} />
                  East Java WBC Relative Impact Map
                </h2>

                <span className="subtle-tag">
                  {mapRegions.length} Regions
                </span>

              </div>

              {mapLoading ? (
                <p>Loading regional map...</p>
              ) : (
                <EastJavaMap
                  selected={myLocation}
                  onSelect={handleMyLocationChange}
                  mapRegions={mapRegions}
                  riskData={riskData}
                />
              )}

              <div className="map-legend">

                <span>
                  <i style={{ background: RISK_COLORS.low }} />
                  Low
                </span>

                <span>
                  <i style={{ background: RISK_COLORS.moderate }} />
                  Moderate
                </span>

                <span>
                  <i style={{ background: RISK_COLORS.high }} />
                  High
                </span>

                <span>
                  <i style={{ background: RISK_COLORS.critical }} />
                  Critical
                </span>

                <span>
                  <i style={{ background: RISK_COLORS.nodata }} />
                  No Data
                </span>

              </div>

              <small>
                Risk levels represent relative comparisons
                of reported affected areas across regions.
                They are not validated biological outbreak thresholds.
                No reported attack does not necessarily mean
                the region is pest-free.
              </small>

            </article>

            {/* HISTORICAL CHART */}

            <article className="panel chart-panel">

              <div className="panel-heading">
                <h2>
                  <TrendingUp size={18} />
                  Historical Affected Area – {myLocation}
                </h2>

                <span className="subtle-tag">
                  Historical Data
                </span>
              </div>

              <div className="chart-box">

                {mineTrend.length > 0 ? (

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <AreaChart data={mineTrend}>

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
                            stopOpacity={0.28}
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
                        dataKey="month"
                        tick={{ fontSize: 10 }}
                      />

                      <YAxis
                        tick={{ fontSize: 11 }}
                        unit=" ha"
                      />

                      <Tooltip
                        formatter={(value) => [
                          `${fmt(value)} ha`,
                          "Affected Area"
                        ]}
                      />

                      <Area
                        type="monotone"
                        dataKey="affected"
                        name="Affected Area"
                        stroke="#e24b4b"
                        strokeWidth={3}
                        fill="url(#mineFill)"
                      />

                    </AreaChart>
                  </ResponsiveContainer>

                ) : (
                  <div className="chart-empty">
                    No historical WBC records available
                    for this region.
                  </div>
                )}

              </div>

            </article>

            {/* REGIONAL RISK GAUGE */}

            <article className="panel risk-panel">

              <div className="panel-heading">
                <h2>
                  <ShieldAlert size={18} />
                  Regional Risk Indicator
                </h2>
              </div>

              <div className="risk-gauge">
                <div className="gauge-arc" />

                <div
                  className="gauge-needle"
                  style={{
                    transform: `rotate(${needleAngle}deg)`,
                    backgroundColor: current.color
                  }}
                />

              </div>

              <strong
                className="risk-word"
                style={{ color: current.color }}
              >
                {current.label}
              </strong>

              <p>
                {!current.hasData
                  ? "Regional WBC observations are unavailable for the latest period."
                  : isSafe
                    ? "No affected area was recorded in the latest available dataset."
                    : `A reported affected area of ${fmt(current.value)} ha has been recorded.`}
              </p>

              {current.hasData && (
                <div className="summary-row">
                  <span>Reported Crop Failure</span>
                  <b>{fmt(current.puso)} ha</b>
                </div>
              )}

              <small>
                Indicator position represents relative
                reported impact, not a validated outbreak probability.
              </small>

            </article>

          </section>

          {/* REGIONAL COMPARISON AND RECOMMENDATIONS */}

          <section className="bottom-grid">

            <article className="panel">

              <div className="panel-heading">
                <h2>
                  <Activity size={18} />
                  Regional Affected Area Comparison
                </h2>
              </div>

              <div className="risk-bars">

                {riskData
                  .filter((item) => item.hasData)
                  .slice()
                  .sort(
                    (a, b) =>
                      Number(b.value) - Number(a.value)
                  )
                  .map((region) => (
                    <div
                      className="risk-bar-row"
                      key={region.name}
                    >
                      <span>{region.name}</span>

                      <div>
                        <i
                          style={{
                            width: `${Math.max(
                              0,
                              Math.min(
                                100,
                                Number(region.score || 0) * 100
                              )
                            )}%`,
                            background: region.color
                          }}
                        />
                      </div>

                      <b>
                        {fmt(region.value)} ha
                      </b>
                    </div>
                  ))}

                {riskData.filter((item) => item.hasData).length === 0 && (
                  <p>No regional comparison data available.</p>
                )}

              </div>

            </article>

            <article className="panel recommendation-panel">

              <div className="panel-heading">
                <h2>
                  <Leaf size={18} />
                  Mitigation Recommendations
                </h2>
              </div>

              {localRecommendations.map(
                (recommendation, index) => (
                  <p key={index}>
                    <CheckCircle2 size={17} />
                    {recommendation}
                  </p>
                )
              )}

            </article>

          </section>

          {/* DATA SOURCES */}

          <section className="panel" style={{ padding: 18 }}>

            <div className="panel-heading">
              <h2>
                <Database size={18} />
                Data Sources and Status
              </h2>
            </div>

            <p>
              <b>NASA POWER:</b> temperature, relative humidity,
              and rainfall data, subject to dataset availability.
            </p>

            <p>
              <b>SiPerDitTan:</b> reported WBC affected area
              and crop failure records.
            </p>

            <p>
              <b>Backend Status:</b>{" "}
              {apiReady ? "Connected" : "Not Connected"}
            </p>

            <p>
              <b>Weather Data Period:</b>{" "}
              {apiHealth?.datasets?.nasa_power?.start || "—"}
              {" – "}
              {apiHealth?.datasets?.nasa_power?.end || "—"}
            </p>

            <p>
              <b>Latest WBC Record:</b> {latestRecordLabel}
            </p>

          </section>

        </main>
      )}

      {/* ============================================== */}
      {/* WBC PREDICTION DASHBOARD */}
      {/* ============================================== */}

      {tab === "prediction" && (

        <main className="dashboard">

          <section className="prediction-title">

            <div>
              <span className="eyebrow">
                REGION AND TIME-BASED ANALYSIS
              </span>

              <h1>
                WBC Population and Attack Forecast
              </h1>

              <p>
                Analyze potential Brown Planthopper affected
                areas based on the selected region and period.
              </p>
            </div>

            <div className="title-icon">
              <CalendarDays size={34} />
            </div>

          </section>

          {/* PREDICTION FORM */}

          <section className="prediction-controls panel">

            <label>
              <span>
                <MapPin size={16} />
                Select Region
              </span>

              <select
                value={predictionLocation}
                onChange={(event) =>
                  handlePredictionLocationChange(
                    event.target.value
                  )
                }
              >
                {locations.map((location) => (
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
                Start Date
              </span>

              <input
                type="date"
                value={startDate}
                onChange={(event) => {
                  setStartDate(event.target.value);
                  setPredictionResult(null);
                  setPredictionError("");
                  setPredicted(false);
                }}
              />
            </label>

            <label>
              <span>
                <CalendarDays size={16} />
                End Date
              </span>

              <input
                type="date"
                value={endDate}
                min={startDate}
                onChange={(event) => {
                  setEndDate(event.target.value);
                  setPredictionResult(null);
                  setPredictionError("");
                  setPredicted(false);
                }}
              />
            </label>

            <button
              className="primary-button"
              onClick={handlePrediction}
              disabled={predictionLoading}
            >
              {predictionLoading ? (
                <RefreshCw size={17} />
              ) : (
                <Activity size={17} />
              )}

              {predictionLoading
                ? "Processing..."
                : "Generate Prediction"}

              <ChevronRight size={17} />
            </button>

          </section>

          {/* PREDICTION ERROR */}

          {predictionError && (
            <div
              className="panel"
              style={{
                padding: 16,
                marginTop: 14,
                color: "#b42318",
                background: "#fff1f0"
              }}
            >
              <AlertTriangle size={18} />
              {" "}{predictionError}
            </div>
          )}

          {/* MAP AND PREDICTION SUMMARY */}

          <section className="prediction-map-row">

            <article className="panel prediction-map-panel">

              <div className="panel-heading">
                <h2>
                  <Map size={18} />
                  Regional Prediction Map
                </h2>

                <span className="subtle-tag">
                  38 Regions
                </span>
              </div>

              <EastJavaMap
                selected={predictionLocation}
                onSelect={handlePredictionLocationChange}
                mapRegions={mapRegions}
                riskData={riskData}
                large
              />

              <small>
                This map displays the latest historical
                observations, not future prediction results.
              </small>

            </article>

            <article className="panel prediction-summary">

              <div className="panel-heading">
                <h2>
                  <Activity size={18} />
                  Prediction Summary
                </h2>
              </div>

              <div className="summary-number">
                <span>
                  Total Predicted Affected Area
                </span>

                <strong>
                  {predicted
                    ? `${fmt(predictionResult?.total_predicted_ha)} ha`
                    : "—"}
                </strong>
              </div>

              <div className="summary-row">
                <span>
                  <MapPin size={16} />
                  Region
                </span>

                <b>{predictionLocation}</b>
              </div>

              <div className="summary-row">
                <span>
                  <CalendarDays size={16} />
                  Period
                </span>

                <b>
                  {titleDate(startDate)}
                  {" – "}
                  {titleDate(endDate)}
                </b>
              </div>

              <div className="summary-row">
                <span>
                  <ShieldAlert size={16} />
                  Potential Attack Periods
                </span>

                <b>
                  {predicted
                    ? predictionSummary.potentialPeriods
                    : "—"}
                </b>
              </div>

              <div className="summary-row">
                <span>Average Probability</span>

                <b>
                  {predicted
                    ? `${fmt(
                        predictionSummary.averageProbability * 100
                      )}%`
                    : "—"}
                </b>
              </div>

              <div className="summary-row">
                <span>Highest Probability</span>

                <b>
                  {predicted
                    ? `${fmt(
                        predictionSummary.highestProbability * 100
                      )}%`
                    : "—"}
                </b>
              </div>

              <div className="summary-note">
                <Info size={15} />

                {predicted
                  ? "The results below are generated by the backend model. Interpret them according to the model's experimental status."
                  : "Select a region and period, then click Generate Prediction."}
              </div>

            </article>

          </section>

          {/* PREDICTION CHARTS */}

          <section className="prediction-charts">

            {/* AFFECTED AREA FORECAST */}

            <article className="panel">

              <div className="panel-heading">
                <h2>
                  <TrendingUp size={18} />
                  Projected WBC Affected Area
                </h2>

                <span className="subtle-tag">
                  AI Model Output
                </span>
              </div>

              <div className="chart-box tall">

                {predicted && predictionItems.length > 0 ? (

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <AreaChart data={predictionItems}>

                      <defs>
                        <linearGradient
                          id="predictionFill"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="0%"
                            stopColor="#f28a24"
                            stopOpacity={0.3}
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
                        dataKey="label"
                        tick={{ fontSize: 11 }}
                      />

                      <YAxis
                        unit=" ha"
                        tick={{ fontSize: 11 }}
                      />

                      <Tooltip
                        formatter={(value) => [
                          `${fmt(value)} ha`,
                          "Predicted Affected Area"
                        ]}
                      />

                      <Area
                        type="monotone"
                        dataKey="predicted_affected_ha"
                        name="Predicted Affected Area"
                        stroke="#f28a24"
                        strokeWidth={3}
                        fill="url(#predictionFill)"
                      />

                    </AreaChart>
                  </ResponsiveContainer>

                ) : (
                  <div className="chart-empty">
                    {predictionLoading
                      ? "The model is processing the prediction..."
                      : "The chart will appear after a successful prediction."}
                  </div>
                )}

              </div>

            </article>

            {/* ATTACK PROBABILITY */}

            <article className="panel">

              <div className="panel-heading">
                <h2>
                  <Activity size={18} />
                  Potential Attack Probability
                </h2>
              </div>

              <div className="chart-box tall">

                {predicted && predictionItems.length > 0 ? (

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <BarChart data={predictionItems}>

                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#e7eee8"
                      />

                      <XAxis
                        dataKey="label"
                        tick={{ fontSize: 11 }}
                      />

                      <YAxis
                        domain={[0, 1]}
                        tickFormatter={(value) =>
                          `${Math.round(value * 100)}%`
                        }
                      />

                      <Tooltip
                        formatter={(value) => [
                          `${fmt(Number(value) * 100)}%`,
                          "Probability"
                        ]}
                      />

                      <Bar
                        dataKey="probability"
                        name="Probability"
                        fill="#239a61"
                        radius={[5, 5, 0, 0]}
                      />

                    </BarChart>
                  </ResponsiveContainer>

                ) : (
                  <div className="chart-empty">
                    No prediction probability data available.
                  </div>
                )}

              </div>

            </article>

          </section>

          {/* PREDICTION TABLE */}

          <section
            className="panel"
            style={{ padding: 18 }}
          >

            <div className="panel-heading">
              <h2>
                <Database size={18} />
                Detailed Prediction Results
              </h2>
            </div>

            {predicted && predictionItems.length > 0 ? (

              <div style={{ overflowX: "auto" }}>

                <table className="prediction-table">

                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Probability</th>
                      <th>Predicted Affected Area</th>
                      <th>Model Status</th>
                    </tr>
                  </thead>

                  <tbody>
                    {predictionItems.map((item, index) => (
                      <tr
                        key={item.date || index}
                      >

                        <td>{item.date || "—"}</td>

                        <td>
                          {fmt(item.probability * 100)}%
                        </td>

                        <td>
                          {fmt(item.predicted_affected_ha)} ha
                        </td>

                        <td>
                          {item.risk || "Not specified"}
                        </td>

                      </tr>
                    ))}
                  </tbody>

                </table>

              </div>

            ) : (
              <p>
                Prediction results are not yet available.
              </p>
            )}

          </section>

          {/* MODEL EVALUATION */}

          {apiMetrics && (
            <section
              className="panel"
              style={{ padding: 18 }}
            >

              <div className="panel-heading">
                <h2>
                  <Activity size={18} />
                  Initial AI Model Evaluation
                </h2>

                <span className="subtle-tag">
                  Experimental
                </span>
              </div>

              <p>
                {apiMetrics.note ||
                  "Model evaluation based on the currently available testing results."}
              </p>

              <h3>Classification</h3>

              {(apiMetrics.classification || []).map(
                (metric, index) => (
                  <div
                    key={`classification-${index}`}
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

              <h3>Regression</h3>

              {(apiMetrics.regression || []).map(
                (metric, index) => (
                  <div
                    key={`regression-${index}`}
                    className="summary-row"
                  >
                    <span>
                      {metric.MODEL ||
                        metric.model ||
                        "Regression Model"}
                    </span>

                    <b>
                      RMSE: {fmt(metric.RMSE ?? metric.rmse, 3)}
                      {" · "}
                      MAE: {fmt(metric.MAE ?? metric.mae, 3)}
                    </b>
                  </div>
                )
              )}

            </section>
          )}

          {/* MODEL INTERPRETATION */}

          <section
            className="panel"
            style={{ padding: 18 }}
          >

            <div className="panel-heading">
              <h2>
                <Info size={18} />
                Prediction Interpretation
              </h2>
            </div>

            <p>
              The current prediction model is experimental.
              Its outputs do not guarantee that an outbreak
              will occur and should not be used as the sole
              basis for field control decisions.
            </p>

            <p>
              The currently identified backend model uses
              Random Forest Classifier and Dummy Regressor.
              Therefore, the predictive performance for
              affected-area estimation should be evaluated
              further before operational deployment.
            </p>

          </section>

        </main>
      )}

      {/* FOOTER */}

      <footer className="footer">

        <span>
          © 2026 PestCycle AI
        </span>

        <span>
          Brown Planthopper Early Warning & Forecasting
          · East Java, Indonesia
        </span>

      </footer>

    </div>
  );
}
