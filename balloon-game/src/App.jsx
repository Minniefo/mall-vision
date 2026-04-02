import React, { useState } from "react";
import BalloonGame from "./BalloonGame";
import Dashboard from "./dashboard/Dashboard";
import "./App.css";


export default function App() {
  const [activeTab, setActiveTab] = useState("kiosk");

  return (
    <div className="app-root">

      {/* 🔷 HEADER */}
      <header className="top-header">
        <div className="brand">MALLVISION</div>

        <div className="nav-tabs">
          <button
            className={`tab ${activeTab === "kiosk" ? "active" : ""}`}
            onClick={() => setActiveTab("kiosk")}
          >
            Kiosk
          </button>

          <button
            className={`tab ${activeTab === "admin" ? "active" : ""}`}
            onClick={() => setActiveTab("admin")}
          >
            Admin
          </button>
        </div>
      </header>

      {/* 🔷 CONTENT */}
      <main className="main-content">
        {activeTab === "kiosk" && <BalloonGame />}
        {activeTab === "admin" && <Dashboard />}
      </main>
    </div>
  );
}

