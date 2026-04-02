import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import BalloonGame from "./BalloonGame";
import PhotoBooth from "./PhotoBooth";
import Dashboard from "./dashboard/Dashboard";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/*<Route path="/kiosk" element={<BalloonGame />} />*/}
        <Route path="/kiosk" element={<PhotoBooth />} />
        <Route path="/admin" element={<Dashboard />} />
        <Route path="/" element={<Navigate to="/kiosk" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);