import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Pie } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const API_BASE = "http://localhost:8000";

function normalizeDecisionLabel(label) {
  if (!label) return "unknown";
  const s = String(label).toLowerCase();
  if (s === "returning") return "returning";
  if (s === "new") return "new";
  return s;
}

export default function NewVsReturningChart({ fromDate, toDate }) {

  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    let mounted = true;
    let interval;

    async function fetchData() {
      try {
        setLoading(true);
        setErr("");

        const res = await axios.get(`${API_BASE}/analytics/new-vs-returning`, {
          params: {
            from: fromDate,
            to: toDate
          }
        });

        if (!mounted) return;
        setRows(Array.isArray(res.data) ? res.data : []);

      } catch (e) {
        if (!mounted) return;
        setErr("Failed to load analytics data.");
        setRows([]);

      } finally {
        if (mounted) setLoading(false);
      }
    }

    fetchData();
    interval = setInterval(fetchData, 5000);

    return () => {
      mounted = false;
      clearInterval(interval);
    };

  }, [fromDate, toDate]);

  const { labels, values, total } = useMemo(() => {

    const counts = {};

    for (const r of rows) {
      const label = normalizeDecisionLabel(r?._id);
      const count = Number(r?.count ?? 0);
      counts[label] = (counts[label] || 0) + count;
    }

    const newCount = counts["new"] || 0;
    const returningCount = counts["returning"] || 0;

    const labelsOut = ["new", "returning"];
    const valuesOut = [newCount, returningCount];

    const totalOut = valuesOut.reduce((a, b) => a + b, 0);

    return { labels: labelsOut, values: valuesOut, total: totalOut };

  }, [rows]);

  const chartData = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: ["#4CAF50", "#2196F3"],
        borderColor: "#ffffff",
        borderWidth: 2,
      },
    ],
  };

  if (loading) {
    return (
      <div className="card">
        <h3>New vs Returning</h3>
        <p>Loading…</p>
      </div>
    );
  }

  if (err) {
    return (
      <div className="card">
        <h3>New vs Returning</h3>
        <p style={{ color: "crimson" }}>{err}</p>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="card">
        <h3>New vs Returning</h3>
        <p>No identity events yet.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>New vs Returning</h3>

      <div style={{ width: 320, maxWidth: "100%" }}>
        <Pie data={chartData} />
      </div>

      <div style={{ marginTop: 10, fontSize: 14 }}>
        <p><b>Total sessions:</b> {total}</p>
        <p><b>New:</b> {values[0]}</p>
        <p><b>Returning:</b> {values[1]}</p>
      </div>
    </div>
  );
}