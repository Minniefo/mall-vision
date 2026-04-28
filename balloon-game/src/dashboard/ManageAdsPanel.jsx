import React, { useState } from "react";
import axios from "axios";

const API_BASE = "http://localhost:8000";

export default function ManageAdsPanel() {
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
  );
}
