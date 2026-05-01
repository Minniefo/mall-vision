import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { Doughnut } from "react-chartjs-2";
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(ArcElement, Tooltip, Legend);

const API_BASE = "http://localhost:8000";

const EMOTION_COLORS = {
  happy: "#FFD700",    // Gold
  sad: "#4682B4",      // SteelBlue
  angry: "#FF4500",    // OrangeRed
  surprise: "#9370DB", // MediumPurple
  neutral: "#A9A9A9",  // DarkGray
  disgust: "#556B2F",  // DarkOliveGreen
  fear: "#4B0082",     // Indigo
};

export default function EmotionChart({ fromDate, toDate }) {
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

        const res = await axios.get(`${API_BASE}/analytics/emotion-distribution`, {
          params: {
            from: fromDate,
            to: toDate
          }
        });

        if (!mounted) return;
        setRows(Array.isArray(res.data) ? res.data : []);

      } catch (e) {
        if (!mounted) return;
        setErr("Failed to load emotion data.");
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

  const { labels, values, colors, total } = useMemo(() => {
    const labelsOut = [];
    const valuesOut = [];
    const colorsOut = [];
    let totalOut = 0;

    rows.forEach(r => {
      const emotion = r._id;
      const count = r.count;
      labelsOut.push(emotion.charAt(0).toUpperCase() + emotion.slice(1));
      valuesOut.push(count);
      colorsOut.push(EMOTION_COLORS[emotion.toLowerCase()] || "#cccccc");
      totalOut += count;
    });

    return { labels: labelsOut, values: valuesOut, colors: colorsOut, total: totalOut };
  }, [rows]);

  const chartData = {
    labels,
    datasets: [
      {
        data: values,
        backgroundColor: colors,
        borderColor: "#ffffff",
        borderWidth: 2,
      },
    ],
  };

  const options = {
    plugins: {
      legend: {
        position: 'bottom',
      }
    },
    maintainAspectRatio: false
  };

  if (loading && rows.length === 0) {
    return (
      <div className="card">
        <h3>Emotion Distribution</h3>
        <p>Loading…</p>
      </div>
    );
  }

  if (err && rows.length === 0) {
    return (
      <div className="card">
        <h3>Emotion Distribution</h3>
        <p style={{ color: "crimson" }}>{err}</p>
      </div>
    );
  }

  if (total === 0) {
    return (
      <div className="card">
        <h3>Emotion Distribution</h3>
        <p>No emotion data yet.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Emotion Distribution</h3>
      <div style={{ height: 250, position: 'relative' }}>
        <Doughnut data={chartData} options={options} />
      </div>
      <div style={{ marginTop: 10, fontSize: 14 }}>
        <p><b>Total detections:</b> {total}</p>
      </div>
    </div>
  );
}
