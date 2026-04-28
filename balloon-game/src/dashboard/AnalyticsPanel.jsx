import React, { useEffect, useState } from "react";
import axios from "axios";
import NewVsReturningChart from "./NewVsReturningChart";
import HourlyTrendChart from "./HourlyTrendChart";
import ReturningByAgeChart from "./ReturningByAgeChart";
import AgeGenderChart from "./AgeGenderChart";

const API_BASE = "http://localhost:8000";

export default function AnalyticsPanel() {
  const [alerts, setAlerts] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [summary, setSummary] = useState(null);

  // 🔥 Security polling
  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const res = await axios.get(`${API_BASE}/analytics/security-alerts`, {
          params: { from: fromDate, to: toDate }
        });
        setAlerts(res.data || []);
      } catch (e) {
        console.error("Failed to fetch alerts");
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 5000);
    return () => clearInterval(interval);
  }, [fromDate, toDate]);

  // 🔥 Behaviour anomaly polling
  useEffect(() => {
    const fetchAnomalies = async () => {
      try {
        const res = await axios.get(`${API_BASE}/analytics/anomaly-alerts`, {
          params: { from: fromDate, to: toDate }
        });
        setAnomalies(res.data || []);
      } catch (e) {
        console.error("Failed to fetch anomalies");
      }
    };

    fetchAnomalies();
    const interval = setInterval(fetchAnomalies, 5000);
    return () => clearInterval(interval);
  }, [fromDate, toDate]);

  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const res = await axios.get(`${API_BASE}/analytics/summary-stats`, {
          params: { from: fromDate, to: toDate }
        });
        setSummary(res.data);
      } catch {
        console.error("Failed to fetch summary stats");
      }
    };

    fetchSummary();
  }, [fromDate, toDate]);

  const ALERT_LIVE_MS = 10000; // 10 seconds

  const latestAlert = alerts && alerts.length > 0
    ? alerts
        .filter((a) => Date.now() - new Date(a.timestamp).getTime() < ALERT_LIVE_MS)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]
    : null;

  const latestAnomaly = anomalies && anomalies.length > 0
    ? anomalies
        .filter((a) => Date.now() - new Date(a.timestamp).getTime() < ALERT_LIVE_MS)
        .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]
    : null;

  return (
    <>
      {/* 🚨 Emotion Alert */}
      {latestAlert && (
        <div className="alert-banner emotion-alert">
          🚨 EMOTION ALERT: {latestAlert.alert_reason?.toUpperCase()}
          <span className="alert-time">
            {new Date(latestAlert.timestamp).toLocaleTimeString(("en-US", {
              timeZone: "Asia/Colombo"
            }))}
          </span>
        </div>
      )}

      {/* 🚨 Behaviour Alert */}
      {latestAnomaly && (
        <div className="alert-banner behaviour-alert">
          🚨 BEHAVIOUR ALERT: {latestAnomaly.anomaly_type?.toUpperCase()}
          <span className="alert-time">
            Track {latestAnomaly.track_id}
          </span>
        </div>
      )}

      {/* DATE FILTER */}
      <div className="date-filter">
        <div className="date-field">
          <label>From</label>
          <input
            type="date"
            value={fromDate}
            onChange={(e) => setFromDate(e.target.value)}
          />
        </div>

        <div className="date-field">
          <label>To</label>
          <input
            type="date"
            value={toDate}
            onChange={(e) => setToDate(e.target.value)}
          />
        </div>
      </div>

      {/*Cards*/}
      <p style={{ fontSize: 12, color: "#666" }}>
        Showing data from {fromDate} to {toDate}
      </p>
      {summary && (
        <div className="summary-grid">
          <div className="summary-card">
            <h4>👁 Total Detections</h4>
            <p>{summary.total_detections.toLocaleString()}</p>
          </div>
          <div className="summary-card">
            <h4>👥 Unique Visitors</h4>
            <p>{summary.total_visitors}</p>
          </div>
          <div className="summary-card">
            <h4>🔁 Returning</h4>
            <p>{summary.returning}</p>
          </div>
          <div className="summary-card">
            <h4>🆕 New</h4>
            <p>{summary.new}</p>
          </div>
          <div className="summary-card highlight">
            <h4>📊 Returning Rate</h4>
            <p>{summary.returning_rate}%</p>
          </div>
        </div>
      )}

      <div className="dashboard-grid">
        <div className="dashboard-card"><AgeGenderChart fromDate={fromDate} toDate={toDate} /></div>
        <div className="dashboard-card"><NewVsReturningChart fromDate={fromDate} toDate={toDate} /></div>
        <div className="dashboard-card"><HourlyTrendChart fromDate={fromDate} toDate={toDate} /></div>
        <div className="dashboard-card"><ReturningByAgeChart fromDate={fromDate} toDate={toDate} /></div>
      </div>

      {/* 🚨 ALERT HISTORY PANEL */}
      <div className="alert-history-card">
        <h3>Recent Security Events (Last 30s)</h3>
        {[...alerts, ...anomalies]
          .filter((event) => Date.now() - new Date(event.timestamp).getTime() < ALERT_LIVE_MS)
          .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
          .slice(0, 6)
          .map((event, index) => (
            <div key={index} className="alert-row">
              <div className={`alert-type ${event.alert_reason ? "emotion" : "behaviour"}`}>
                {event.alert_reason ? "Emotion" : "Behaviour"}
              </div>
              <div className="alert-desc">
                {(event.alert_reason || event.anomaly_type)?.toUpperCase()}
              </div>
              <div className="alert-time">
                {new Date(event.timestamp).toLocaleTimeString(("en-US", {
                  timeZone: "Asia/Colombo"
                }))}
              </div>
            </div>
          ))}
        {alerts.length === 0 && anomalies.length === 0 && (
          <p className="no-alerts">No recent alerts</p>
        )}
      </div>
    </>
  );
}
