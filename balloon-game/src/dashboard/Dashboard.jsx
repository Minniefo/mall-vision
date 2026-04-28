//Dashboard.jsx

import React, { useState } from "react";
import AnalyticsPanel from "./AnalyticsPanel";
import ManageAdsPanel from "./ManageAdsPanel";
import "./dashboard.css";

export default function Dashboard() {
  const [activeTab, setActiveTab] = useState("analytics");

  return (
    <div className="dashboard-container">
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

      {activeTab === "analytics" ? <AnalyticsPanel /> : <ManageAdsPanel />}
    </div>
  );
}