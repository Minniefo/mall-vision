// balloon-game/src/MassAudience.jsx
import React, { useEffect, useState } from "react";
import axios from "axios";
import "./MassAudience.css";

function MassAudience({ screen}) {
  const [massAdImage, setMassAdImage] = useState(null);
  const [massAge, setMassAge] = useState(null);
  const [massGender, setMassGender] = useState(null);
  const [massEmotion, setMassEmotion] = useState(null);
  const [massEngagement, setMassEngagement] = useState(null);
  const [adSource, setAdSource] = useState(null);
  const [detectedObject, setDetectedObject] = useState(null);
  const [adType, setAdType] = useState(null);
  const [isVisible, setIsVisible] = useState(false);
  const getEngagementStatus = () => {
          if (massEngagement === null) return null;

          if (massEngagement > 60) return "HIGH";
          if (massEngagement > 30) return "MEDIUM";
          return "LOW";
        };

  /*useEffect(() => {
    //if (isGameRunning) return;

    const interval = setInterval(async () => {

      const isIdleScreen = document.querySelector(".idle-screen");
      if (!isIdleScreen) return;

      try {
        // 1️⃣ Capture frame from existing webcam video
        const video = document.querySelector("video");
        if (!video) return;

        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth || 320;
        canvas.height = video.videoHeight || 240;

        const ctx = canvas.getContext("2d");
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        const frameBase64 = canvas.toDataURL("image/jpeg");

        // 2️⃣ Send frame to backend (THIS TRIGGERS run_mass_inference)
        await axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/mass_frame`, {
          image: frameBase64,
          session_id: "mass"
        });

        // 3️⃣ Fetch current mass advertisement
        const res = await axios.get(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/current_mass_ad`);


        // const { ad_image, age_group, gender, emotion, engagement_pct, ad_source, detected_object  } = res.data;

        const { 
          ad_image, 
          ad_type,        // 🔥 NEW
          media_url,      // 🔥 NEW (if you use URL instead of base64)
          age_group, 
          gender, 
          emotion, 
          engagement_pct, 
          ad_source, 
          detected_object 
        } = res.data;

        console.log("MASS AD:", {
          age_group,
          gender,
          emotion,
          engagement_pct,
          has_image: !!ad_image,
          image_len: ad_image ? ad_image.length : 0,
          image_preview: ad_image ? ad_image.slice(0, 60) + "..." : null,
        });

        setMassAdImage(res.data.ad_image || null);
        setMassEmotion(res.data.emotion || null);
        setMassAge(res.data.age_group || null);
        setMassGender(res.data.gender || null);
        setMassEngagement(
          engagement_pct !== undefined ? engagement_pct : null
        );
        setAdSource(ad_source || null);
        setDetectedObject(detected_object || null);

      } catch (err) {
        console.error("Mass audience error:", err);
        setMassAdImage(null);
        setMassAge(null);
        setMassGender(null);
        setMassEmotion(null);
        setMassEngagement(null);
        setAdType(res.data.ad_type || null);
        setIsVisible(false);

        setTimeout(() => {
          setIsVisible(true);
        }, 100);

      }
    }, 2000);

    return () => clearInterval(interval);
  //}, [isGameRunning]);
  }, []);*/

  useEffect(() => {
    let interval;

    if (screen === "idle") {
      console.log("🟢 MassAudience STARTED");

      interval = setInterval(async () => {
        try {
          const video = document.querySelector("video");
          if (!video) return;

          const canvas = document.createElement("canvas");
          canvas.width = video.videoWidth || 320;
          canvas.height = video.videoHeight || 240;

          const ctx = canvas.getContext("2d");
          ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

          const frameBase64 = canvas.toDataURL("image/jpeg");

          await axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/mass_frame`, {
            image: frameBase64,
            session_id: "mass"
          });

          const res = await axios.get(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/current_mass_ad`);

          const {
            ad_image,
            age_group,
            gender,
            emotion,
            engagement_pct,
            ad_source,
            detected_object
          } = res.data;

          setMassAdImage(ad_image || null);
          setMassEmotion(emotion || null);
          setMassAge(age_group || null);
          setMassGender(gender || null);
          setMassEngagement(
            engagement_pct !== undefined ? engagement_pct : null
          );
          setAdSource(ad_source || null);
          setDetectedObject(detected_object || null);

        } catch (err) {
          console.error("Mass audience error:", err);
        }
      }, 2000);
    }

    return () => {
      if (interval) {
        console.log("🔴 MassAudience STOPPED");
        clearInterval(interval);
      }
    };

  }, [screen]);

  return (
  <div className="mass-audience-panel">
    <h2 className="mass-title">Trending For You</h2>

    {adSource === "novelty" && detectedObject && (
      <div className="novelty-banner">
        Surprise! We detected a <b>{detectedObject}</b>.  
        Here's something you might like!
      </div>
    )}

    {massAdImage ? (
      <>
        {/*<div className="mass-ad-container">
          <img
            src={massAdImage}
            alt="Mass Advertisement"
            className="mass-ad-img"
          />
        </div>*/}

        <div className="mass-ad-container">
          {adType === "video" ? (
            <video
              src={media_url || massAdImage}
              autoPlay
              loop
              muted
              playsInline
              preload="auto"
              className={`mass-ad-img ${isVisible ? "visible" : ""}`}
            />
          ) : (
            <img
              src={massAdImage}
              alt="Mass Advertisement"
              className={`mass-ad-img ${isVisible ? "visible" : ""}`}
            />
          )}
        </div>

        {(massAge || massGender || massEmotion|| massEngagement !== null) && (
          <div className="mass-demographics">
            <p>
              <b>Detected:</b>{" "}
              {massAge ? massAge : "Unknown"}{" "}
              {massGender ? `(${massGender})` : ""}
              {massEmotion ? `(${massEmotion})` : ""}
            </p>
            {massEngagement !== null && (
              <>
                <p>
                  <b>Audience Engagement:</b> {getEngagementStatus()}
                </p>

                <p>
                  <b>Engagement:</b> {massEngagement.toFixed(1)}%
                </p>
              </>
            )}
          </div>
        )}
      </>
    ) : (
      <p className="no-ad">No audience detected</p>
    )}
  </div>
);

}

export default MassAudience;

