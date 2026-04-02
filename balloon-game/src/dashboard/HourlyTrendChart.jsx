//HourlyTrendChart.jsx
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  LineElement,
  PointElement,
  LinearScale,
  CategoryScale,
  Tooltip,
  Legend
);

const API_BASE = "http://localhost:8000";

// Ensure we always show 24 hours (0–23), even if some have zero counts
function normalizeHourly(rows) {
  const map = new Array(24).fill(0);
  rows.forEach((r) => {
    const hour = Number(r?._id);
    const count = Number(r?.count ?? 0);
    if (!Number.isNaN(hour) && hour >= 0 && hour <= 23) {
      map[hour] = count;
    }
  });
  return map;
}

export default function HourlyTrendChart() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        setLoading(true);
        setErr("");
        const res = await axios.get(`${API_BASE}/analytics/hourly-trend`);
        if (!mounted) return;
        setRows(Array.isArray(res.data) ? res.data : []);
      } catch (e) {
        if (!mounted) return;
        setErr("Failed to load hourly trend.");
        setRows([]);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 5000); // auto-refresh every 5s

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const { labels, values, total } = useMemo(() => {
    const values24 = normalizeHourly(rows);
    const labels24 = Array.from({ length: 24 }, (_, i) =>
      i.toString().padStart(2, "0")
    );
    const totalCount = values24.reduce((a, b) => a + b, 0);
    return { labels: labels24, values: values24, total: totalCount };
  }, [rows]);

  const chartData = useMemo(
    () => ({
      labels,
      datasets: [
        {
          label: "Sessions",
          data: values,
          tension: 0.3,

          // ✅ COLORS
          borderColor: "#3F51B5",              // line color (indigo)
          backgroundColor: "rgba(63,81,181,0.15)", // area fill
          pointBackgroundColor: "#3F51B5",
          pointBorderColor: "#3F51B5",
          pointRadius: 4,

          fill: true,
        },
      ],
    }),
    [labels, values]
  );


  const options = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
        tooltip: { mode: "index", intersect: false },
      },
      scales: {
        x: {
          title: { display: true, text: "Hour of Day" },
          ticks: { autoSkip: false },
        },
        y: {
          title: { display: true, text: "Sessions" },
          beginAtZero: true,
          precision: 0,
        },
      },
    }),
    []
  );

  if (loading) {
    return (
      <div className="card">
        <h3>Hourly Trend</h3>
        <p>Loading…</p>
      </div>
    );
  }

  if (err) {
    return (
      <div className="card">
        <h3>Hourly Trend</h3>
        <p style={{ color: "crimson" }}>{err}</p>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="card">
        <h3>Hourly Trend</h3>
        <p>No identity events yet.</p>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: 320 }}>
      <h3>Hourly Trend</h3>
      <Line data={chartData} options={options} />
      <div style={{ marginTop: 8, fontSize: 14 }}>
        <p><b>Total sessions:</b> {total}</p>
      </div>
    </div>
  );
}
