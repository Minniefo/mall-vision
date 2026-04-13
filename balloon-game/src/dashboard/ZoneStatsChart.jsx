//ZoneStatsChart.jsx
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function normalizeZones(rows) {
  // Ensure stable ordering and handle missing zones
  const counts = {};
  rows.forEach((r) => {
    const zone = String(r?._id ?? "unknown");
    const count = Number(r?.count ?? 0);
    counts[zone] = (counts[zone] || 0) + count;
  });

  // Prefer showing near/far first if present
  const preferredOrder = ["near", "far"];
  const orderedLabels = [
    ...preferredOrder.filter((z) => z in counts),
    ...Object.keys(counts).filter((z) => !preferredOrder.includes(z)),
  ];

  const values = orderedLabels.map((z) => counts[z]);
  const total = values.reduce((a, b) => a + b, 0);

  return { labels: orderedLabels, values, total };
}

export default function ZoneStatsChart() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        setLoading(true);
        setErr("");
        const res = await axios.get(`${API_BASE}/analytics/zone-stats`);
        if (!mounted) return;
        setRows(Array.isArray(res.data) ? res.data : []);
      } catch (e) {
        if (!mounted) return;
        setErr("Failed to load zone statistics.");
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

  const { labels, values, total } = useMemo(
    () => normalizeZones(rows),
    [rows]
  );

  const data = useMemo(
  () => ({
    labels,
    datasets: [
      {
        label: "Sessions",
        data: values,
        backgroundColor: ["#009688", "#FF9800", "#9C27B0"], // near, far, others
        borderRadius: 6,
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
          title: { display: true, text: "Zone" },
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
        <h3>Zone Statistics</h3>
        <p>Loading…</p>
      </div>
    );
  }

  if (err) {
    return (
      <div className="card">
        <h3>Zone Statistics</h3>
        <p style={{ color: "crimson" }}>{err}</p>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="card">
        <h3>Zone Statistics</h3>
        <p>No identity events yet.</p>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: 320 }}>
      <h3>Zone Statistics</h3>
      <Bar data={data} options={options} />
      <div style={{ marginTop: 8, fontSize: 14 }}>
        <p><b>Total sessions:</b> {total}</p>
      </div>
    </div>
  );
}
