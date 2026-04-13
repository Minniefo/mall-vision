//Dashboard.jsx

import React, { useEffect, useState } from "react";
import axios from "axios";
import NewVsReturningChart from "./NewVsReturningChart";
import HourlyTrendChart from "./HourlyTrendChart";
import ZoneStatsChart from "./ZoneStatsChart";
import SimilarityDistChart from "./SimilarityDistChart";
import "./dashboard.css";
import ReturningByAgeChart from "./ReturningByAgeChart";
import AgeGenderChart from "./AgeGenderChart";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Dashboard() {

  const [alerts, setAlerts] = useState([]);
  const [activeTab, setActiveTab] = useState("analytics");
  const [anomalies, setAnomalies] = useState([]);


  // 🔥 Security polling (UNCHANGED)
  useEffect(() => {

  const fetchAlerts = async () => {
    try {

      const res = await axios.get(`${API_BASE}/analytics/security-alerts`);

      console.log("ALERT RESPONSE:", res.data);

      // Backend already filters last 30 seconds
      setAlerts(res.data || []);

    } catch (e) {

      console.error("Failed to fetch alerts");

    }
  };

  fetchAlerts();

  const interval = setInterval(fetchAlerts, 2000);

  return () => clearInterval(interval);

}, []);

  // 🔥 Behaviour anomaly polling
  useEffect(() => {

  const fetchAnomalies = async () => {
    try {

      const res = await axios.get(`${API_BASE}/analytics/anomaly-alerts`);

      console.log("ANOMALY RESPONSE:", res.data);

      // Backend already filters last 30 seconds
      setAnomalies(res.data || []);

    } catch (e) {

      console.error("Failed to fetch anomalies");

    }
  };

  fetchAnomalies();

  const interval = setInterval(fetchAnomalies, 2000);

  return () => clearInterval(interval);

}, []);

  //const latestAlert = alerts.length > 0 ? alerts[0] : null;
  const latestAlert =
  alerts && alerts.length > 0
    ? alerts.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]
    : null;

  const latestAnomaly =
  anomalies && anomalies.length > 0
    ? anomalies.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]
    : null;  

  // -------------------------------
  // Add Ad State
  // -------------------------------
  const [adTitle, setAdTitle] = useState("");
  const [adDescription, setAdDescription] = useState("");
  const [adFile, setAdFile] = useState(null);

  const handleSubmit = async () => {
    if (!adTitle || !adFile) {
      alert("Title and image required");
      return;
    }

    const formData = new FormData();
    formData.append("ad_title", adTitle);
    formData.append("ad_description", adDescription);
    formData.append("file", adFile);

    try {
      const res = await axios.post(
        `${API_BASE}/admin/add-ad`,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );

      if (res.data.success) {
        alert("Ad added! PID: " + res.data.pid);
        setAdTitle("");
        setAdDescription("");
        setAdFile(null);
      } else {
        alert(res.data.message);
      }

    } catch {
      alert("Upload failed");
    }
  };

  return (
    <div className="dashboard-container">

      {/* 🚨 SECURITY ALERT — ALWAYS VISIBLE */}
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

      {/* HEADER */}
<div className="dashboard-header">
  <div className="header-left">
    <h1>MallVision Admin</h1>
    <span className="header-subtitle">
      Advertisement & Analytics Control Panel
    </span>
  </div>

  <div className="admin-tabs">
    <button
      className={`tab-btn ${activeTab === "analytics" ? "active" : ""}`}
      onClick={() => setActiveTab("analytics")}
    >
      <span className="tab-icon">📊</span>
      Analytics
    </button>

    <button
      className={`tab-btn ${activeTab === "ads" ? "active" : ""}`}
      onClick={() => setActiveTab("ads")}
    >
      <span className="tab-icon">🛍</span>
      Manage Ads
    </button>
  </div>
</div>

      {/* TAB CONTENT */}
      {activeTab === "analytics" && (
        <>
            <div className="dashboard-grid">
              <div className="dashboard-card"><AgeGenderChart /></div>
              <div className="dashboard-card"><NewVsReturningChart /></div>
              <div className="dashboard-card"><HourlyTrendChart /></div>
              <div className="dashboard-card"><ReturningByAgeChart /></div>
            </div>

          {/* 🚨 ALERT HISTORY PANEL */}
          <div className="alert-history-card">

            <h3>Recent Security Events (Last 30s)</h3>

            {[...alerts, ...anomalies]
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
      )}

      {activeTab === "ads" && (
  <div className="ads-layout">

    <div className="ads-form-card">
      <h2>Add Advertisement</h2>

      <label>Ad Title</label>
      <input
        type="text"
        value={adTitle}
        onChange={(e) => setAdTitle(e.target.value)}
        placeholder="Enter advertisement title"
      />

      <label>Ad Description</label>
      <textarea
        value={adDescription}
        onChange={(e) => setAdDescription(e.target.value)}
        placeholder="Enter advertisement description"
      />

      <label>Upload Image</label>
      <input
        type="file"
        accept="image/*"
        onChange={(e) => setAdFile(e.target.files[0])}
      />

      <button className="primary-btn" onClick={handleSubmit}>
        Submit Advertisement
      </button>
    </div>

    <div className="ads-preview-card">
      <h3>Preview</h3>

      {adFile ? (
        <img
          src={URL.createObjectURL(adFile)}
          alt="preview"
          className="preview-image"
        />
      ) : (
        <div className="preview-placeholder">
          Image preview will appear here
        </div>
      )}

      <div className="preview-meta">
        <p><strong>Title:</strong> {adTitle || "—"}</p>
        <p><strong>Description:</strong> {adDescription || "—"}</p>
      </div>
    </div>

  </div>
)}
    </div>
  );
}