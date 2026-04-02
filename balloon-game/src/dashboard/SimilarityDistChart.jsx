//SimilarityDistChart.jsx
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

const API_BASE = "http://localhost:8000";

/**
 * Build histogram bins for similarity scores
 * Default: 10 bins (0.0–1.0)
 */
function buildHistogram(rows, binCount = 10) {
  const bins = new Array(binCount).fill(0);

  rows.forEach((r) => {
    const s = Number(r?.similarity_score);
    if (!Number.isNaN(s)) {
      const idx = Math.min(
        binCount - 1,
        Math.floor(s * binCount)
      );
      bins[idx] += 1;
    }
  });

  const labels = bins.map((_, i) => {
    const start = (i / binCount).toFixed(1);
    const end = ((i + 1) / binCount).toFixed(1);
    return `${start}–${end}`;
  });

  const total = bins.reduce((a, b) => a + b, 0);
  return { labels, values: bins, total };
}

export default function SimilarityDistChart() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;

    async function fetchData() {
      try {
        setLoading(true);
        setErr("");
        const res = await axios.get(
          `${API_BASE}/analytics/similarity-distribution`
        );
        if (!mounted) return;
        setRows(Array.isArray(res.data) ? res.data : []);
      } catch (e) {
        if (!mounted) return;
        setErr("Failed to load similarity distribution.");
        setRows([]);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 5000); // auto-refresh

    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const { labels, values, total } = useMemo(
    () => buildHistogram(rows, 10),
    [rows]
  );

  const data = useMemo(
    () => ({
        labels,
        datasets: [
        {
            label: "Identity Events",
            data: values,
            backgroundColor: "#E91E63",
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
          title: { display: true, text: "Similarity Score Range" },
        },
        y: {
          title: { display: true, text: "Count" },
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
        <h3>Similarity Confidence Distribution</h3>
        <p>Loading…</p>
      </div>
    );
  }

  if (err) {
    return (
      <div className="card">
        <h3>Similarity Confidence Distribution</h3>
        <p style={{ color: "crimson" }}>{err}</p>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="card">
        <h3>Similarity Confidence Distribution</h3>
        <p>No identity events yet.</p>
      </div>
    );
  }

  return (
    <div className="card" style={{ height: 320 }}>
      <h3>Similarity Confidence Distribution</h3>
      <Bar data={data} options={options} />
      <div style={{ marginTop: 8, fontSize: 14 }}>
        <p><b>Total identity events:</b> {total}</p>
      </div>
    </div>
  );
}
