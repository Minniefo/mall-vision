import React, { useEffect, useState, useMemo } from "react";
import axios from "axios";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const API_BASE = "http://localhost:8000";

export default function ReturningByAgeChart({ fromDate, toDate }) {

  const [rows, setRows] = useState([]);

  useEffect(() => {
    let interval;

    const fetchData = async () => {
      try {
        const res = await axios.get(`${API_BASE}/analytics/returning-by-age`, {
          params: {
            from: fromDate,
            to: toDate
          }
        });

        setRows(res.data || []);

      } catch (e) {
        console.error("Failed to fetch ReturningByAge data");
        setRows([]);
      }
    };

    fetchData();
    interval = setInterval(fetchData, 5000); // auto-refresh

    return () => clearInterval(interval);

  }, [fromDate, toDate]);

  const { labels, newCounts, returningCounts } = useMemo(() => {

    const ageGroups = ["1-12", "13-19", "20-35", "36+"];
    const newMap = {};
    const returningMap = {};

    rows.forEach(r => {
      if (!r._id) return;

      const age = r._id.age_group;
      const type = r._id.type;
      const count = r.count || 0;

      if (type === "new") newMap[age] = count;
      if (type === "returning") returningMap[age] = count;
    });

    return {
      labels: ageGroups,
      newCounts: ageGroups.map(a => newMap[a] || 0),
      returningCounts: ageGroups.map(a => returningMap[a] || 0)
    };

  }, [rows]);

  const data = {
    labels,
    datasets: [
      {
        label: "New",
        data: newCounts,
        backgroundColor: "#2196F3"
      },
      {
        label: "Returning",
        data: returningCounts,
        backgroundColor: "#FF9800"
      }
    ]
  };

  return (
    <div style={{ height: 320 }}>
      <h3>Returning Customers by Age</h3>
      <Bar data={data} />
    </div>
  );
}