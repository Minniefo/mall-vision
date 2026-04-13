import React, { useRef, useEffect, useState } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import MassAudience from "./MassAudience";
import "./BalloonGamePortrait.css";
import "./MassAudience.css";
import BalloonPopper from "./BalloonGame";

function PhotoBooth() {
  const webcamRef = useRef(null);
  const [timer, setTimer] = useState(30);
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const [finalAge, setFinalAge] = useState(null);
  const [finalGender, setFinalGender] = useState(null);
  const [finalAdImage, setFinalAdImage] = useState(null);
  const [showAdPopup, setShowAdPopup] = useState(false);

  const [visitorType, setVisitorType] = useState(null);
  const [similarityDebug, setSimilarityDebug] = useState(null);
  const [visitCount, setVisitCount] = useState(null);
  const [showReturningPopup, setShowReturningPopup] = useState(false);

  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const [screen, setScreen] = useState("idle"); 
  const [daysSinceLastVisit, setDaysSinceLastVisit] = useState(null);
  const [filteredImage, setFilteredImage] = useState(null);
  const [capturedPhotos, setCapturedPhotos] = useState([]);
  const [captureCount, setCaptureCount] = useState(0);
  const [adTriggered, setAdTriggered] = useState(false);
  const hasTriggeredRef = useRef(false);
  const [experience, setExperience] = useState(null); // "photo" | "balloon" | null
  const USE_UGREEN_CAMERA = false; 
  // true  → use UGREEN USB webcam
  // false → use laptop default webcam
  // "idle" | "game" | "result"

  // -------------------------------
  // Start game (logic unchanged)
  // -------------------------------
  const startGame = async (selectedExperience) => {
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/start_game`);

      console.log("🎮 Start Game response:", res.data);

      const {
        visitor_type,
        visit_count,
        session_id,
        days_since_last_visit
      } = res.data;

      setSessionId(session_id);
      setVisitorType(visitor_type);
      setVisitCount(visit_count);
      setDaysSinceLastVisit(days_since_last_visit);

      // 🔥 Returning user → wait for confirmation
      if (visitor_type === "returning") {
        setExperience(selectedExperience);
        setShowReturningPopup(true);
        return;
      }

      // ✅ Store selected experience
      setExperience(selectedExperience);

      // 🔥 COMMON RESET (safe for both)
      setCapturedPhotos([]);
      setTimer(30);
      setIsRunning(true);
      setCaptureCount(0);
      setAdTriggered(false);
      hasTriggeredRef.current = false;

      // ✅ KEY CHANGE HERE 👇
      if (selectedExperience === "photo") {
        setScreen("game");       // your existing photo booth
      } else if (selectedExperience === "balloon") {
        setScreen("balloon");    // new screen
      }

    } catch (err) {
      console.error("Start game error:", err);
    }
  };

// -------------------------------
// Timer
// -------------------------------
useEffect(() => {
  if (!isRunning) return;

  const interval = setInterval(() => {
    setTimer((prev) => prev - 1);
  }, 1000);

  return () => clearInterval(interval);
}, [isRunning]);

useEffect(() => {
  if (timer <= 0 && isRunning && !hasTriggeredRef.current && experience === "photo") {
    hasTriggeredRef.current = true;

    console.log("⏱ Timer ended → triggering ad");

    setAdTriggered(true);
    setIsRunning(false);
    setTimer(0);

    fetchFinalPrediction();
  }
}, [timer, isRunning]);

  // -------------------------------
  // Prefer external cam (unchanged)
  // -------------------------------
  /*useEffect(() => {
    const selectCamera = async () => {
      try {
        // Ask permission first (so labels are visible)
        await navigator.mediaDevices.getUserMedia({ video: true });

        const devices = await navigator.mediaDevices.enumerateDevices();
        const cameras = devices.filter((d) => d.kind === "videoinput");

        console.log("Available Cameras:", cameras);

        // Strictly look for UGREEN
        const ugreenCam = cameras.find((cam) =>
          cam.label.toLowerCase().includes("ugreen")
        );

        if (ugreenCam) {
          console.log("UGREEN locked:", ugreenCam.label);
          setSelectedDeviceId(ugreenCam.deviceId);
          return;
        }

        // Fallback: USB / UVC devices
        const usbCam = cameras.find((cam) =>
          cam.label.toLowerCase().includes("usb") ||
          cam.label.toLowerCase().includes("uvc")
        );

        if (usbCam) {
          console.log("USB camera locked:", usbCam.label);
          setSelectedDeviceId(usbCam.deviceId);
          return;
        }

        // Final fallback (avoid iPhone & FaceTime)
        const safeFallback = cameras.find(
          (cam) =>
            !cam.label.toLowerCase().includes("facetime") &&
            !cam.label.toLowerCase().includes("iphone")
        );

        if (safeFallback) {
          console.log("Fallback camera:", safeFallback.label);
          setSelectedDeviceId(safeFallback.deviceId);
        }

      } catch (err) {
        console.error("Camera selection error:", err);
      }
    };

    selectCamera();
  }, []);*/

  useEffect(() => {
    const selectCamera = async () => {

      // 🔹 If laptop webcam requested
      if (!USE_UGREEN_CAMERA) {
        console.log("Using default laptop webcam");
        setSelectedDeviceId(null);
        return;
      }

      try {
        const tempStream = await navigator.mediaDevices.getUserMedia({ video: true });
        tempStream.getTracks().forEach(track => track.stop());

        const devices = await navigator.mediaDevices.enumerateDevices();
        const cameras = devices.filter((d) => d.kind === "videoinput");

        console.log("Available Cameras:", cameras);

        const ugreenCam = cameras.find((cam) =>
          cam.label.toLowerCase().includes("ugreen")
        );

        if (ugreenCam) {
          console.log("UGREEN camera locked:", ugreenCam.label);
          setSelectedDeviceId(ugreenCam.deviceId);
          return;
        }

        const usbCam = cameras.find((cam) =>
          cam.label.toLowerCase().includes("usb") ||
          cam.label.toLowerCase().includes("uvc")
        );

        if (usbCam) {
          console.log("USB camera locked:", usbCam.label);
          setSelectedDeviceId(usbCam.deviceId);
          return;
        }

        console.warn("UGREEN camera not found, using default webcam.");
        setSelectedDeviceId(null);

      } catch (err) {
        console.error("Camera selection error:", err);
      }
    };

    selectCamera();
  }, []);

  // -------------------------------
  // Send frames
  // -------------------------------
  const sendFrameToBackend = async (image) => {
    try {
      if (!sessionId) return;

      const res = await axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/upload_frame`, {
        image,
        session_id: sessionId,
        preview: false ,  // 🔥 ADD THIS
        capture: true
      });

      // 🔥 IMPORTANT → update webcam with filtered image
      if (res.data.image) {
        // You need a state for this
        setFilteredImage(`data:image/jpeg;base64,${res.data.image}`);
      }

    } catch (err) {
      console.error("Error sending frame:", err);
    }
  };

  useEffect(() => {
    if (screen !== "game" && screen !== "balloon") return;

    console.log("📸 Checking webcamRef:", webcamRef.current);

    const interval = setInterval(() => {
      if (!webcamRef.current) return;

      const shot = webcamRef.current.getScreenshot();
      console.log("📷 Shot captured:", !!shot);
      if (!shot) return;

      if (sessionId) {
        sendFrameToBackend(shot);
      }
    }, 800);

    return () => clearInterval(interval);
}, [screen, sessionId]);

  // -------------------------------
  // Poll session state for returning popup during game
  // -------------------------------
  /*useEffect(() => {
    if (screen !== "game" || !sessionId|| showReturningPopup) return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/session_state`);
        //const { visitor_type, visit_count, days_since_last_visit } = res.data;
        const { visitor_type, visit_count, days_since_last_visit, similarity_debug } = res.data;

        setSimilarityDebug(similarity_debug);
        setDaysSinceLastVisit(days_since_last_visit);

        // If backend identified a returning customer, show popup and pause game
        if (
          visitor_type === "returning" &&
          !res.data.returning_popup_shown &&
          !showReturningPopup
        ) {
          setIsRunning(false);
          setVisitorType(visitor_type);
          setVisitCount(visit_count);
          setShowReturningPopup(true);
        }
      } catch (err) {
        console.error("Error polling session state:", err);
      }
    }, 2500); // Poll every 1 second

    return () => clearInterval(pollInterval);
  }, [screen, sessionId, showReturningPopup]);*/


  // -------------------------------
  const fetchFinalPrediction = async () => {
    try {
      const res = await axios.get(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/final_prediction`);
      console.log("FINAL PREDICTION RESPONSE:", res.data);

      if (res.data.error) {
        console.warn("No predictions:", res.data.error);
        return;
      }

      setFinalAge(res.data.age_group);
      setFinalGender(res.data.gender);
      setFinalAdImage(res.data.advertisement_image);

      setVisitorType(res.data.visitor_type);
      setVisitCount(res.data.visit_count);
      setScreen("result");
      setShowAdPopup(true);
    } catch (err) {
      console.error("Final prediction error:", err);
    }
  };

  const confirmReturningStart = async () => {
    try {
      await axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/acknowledge_returning`);
    } catch (e) {
      console.error("Acknowledge failed:", e);
    }

    setShowReturningPopup(false);

    // ✅ NOW enter photo booth
    if (experience === "photo") {
      setCapturedPhotos([]);
      setScreen("game");
      setTimer(30);
      setIsRunning(true);
      setCaptureCount(0);
      setAdTriggered(false);
      hasTriggeredRef.current = false;
    } else if (experience === "balloon") {
      setScreen("balloon");
    }
  };

const handleCapture = async () => {
  console.log("📸 Capture clicked");

  if (!webcamRef.current) return;

  //const image = webcamRef.current.getScreenshot();
  const image = filteredImage || webcamRef.current.getScreenshot();
  if (!image) return;

  // ✅ Save photo
  setCapturedPhotos((prev) => {
    const updated = [...prev, image];
    return updated.slice(-5);
  });

  try {
    // ✅ SEND FRAMES FIRST
    for (let i = 0; i < 5; i++) {
      await axios.post("http://localhost:8000/upload_frame", {
        image,
        session_id: sessionId,
        preview: false,
        capture: false
      });
    }

    console.log("📸 Frames sent to backend");

    // 🔥 NOW update capture count AFTER frames
    {/*setCaptureCount((prev) => {
      const newCount = prev + 1;

      console.log("📸 Capture count:", newCount);

      if (!adTriggered && newCount >= 3) {
        console.log("🎯 3 captures reached → triggering ad");

        setAdTriggered(true);
        fetchFinalPrediction(); // ✅ NOW SAFE
      }

      return newCount;
    });*/}

    const newCount = captureCount + 1;
    setCaptureCount(newCount);

    console.log("📸 Capture count:", newCount);

    if (!adTriggered && newCount >= 3) {
      console.log("🎯 3 captures reached → triggering ad");

      setAdTriggered(true);
      setIsRunning(false); // 🔥 STOP TIMER
      hasTriggeredRef.current = true;
      fetchFinalPrediction();
    }

  } catch (err) {
    console.error("❌ Capture error:", err);
  }
};

return (

  <div className="kiosk-portrait-root">

    {/* IDLE SCREEN */}
    {screen === "idle" && (
    <div className="idle-screen">

        <div className="idle-hero">
        <div className="idle-title">MALL VISION</div>
        <div className="idle-subtitle">
            FROM FACES TO INSIGHTS
        </div>
        </div>

        {/* 🔵 Live Camera in Idle */}
        <div className="idle-camera">
        <div className="section-label">Live Camera</div>
        <Webcam
          audio={false}
          ref={webcamRef}
          screenshotFormat="image/jpeg"
          width={360}
          height={240}
          className="webcam-frame"
          videoConstraints={{
            deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,
            width: 1280,
            height: 720,
          }}
        />
        
        </div>

    {/* 🔵 Mass Audience Recommendation */}
    <div className="idle-mass">
      <MassAudience screen={screen} />
    </div>

    <div className="idle-cta">
      <button className="start-btn-modern" onClick={() => startGame("photo")}>
        📸 Photo Booth
      </button>

      <button className="start-btn-modern secondary-btn" onClick={() => startGame("balloon")}>
        🎈 Balloon Popper
      </button>
    </div>

  </div>
)}

    {/* GAME SCREEN */}
    {screen === "game" && (
      <>
        {/* your existing top bar + canvas + camera + mass removed */}
        <div className="kiosk-top">
          <div className="kiosk-title">AI Photo Booth</div>
          <div className="kiosk-metrics">
            <div className="metric-box">⏱ {timer}s</div>
          </div>
        </div>

        

        <div className="camera-wrap">
          <div className="section-label">Your Camera</div>
          <div className="camera-container">
  <Webcam
    audio={false}
    ref={webcamRef}
    screenshotFormat="image/jpeg"
    width={360}
    height={240}
    className="webcam-frame"
  />

  {filteredImage && (
    <img
      src={filteredImage}
      className="filter-overlay"
      width={360}
      height={240}
    />
  )}
</div>
         </div>
         <button className="capture-btn" onClick={handleCapture}>
            📸 Capture
        </button>


        {capturedPhotos.length > 0 && (
          <img
            src={capturedPhotos[capturedPhotos.length - 1]}
            alt="Latest"
            className="main-preview"
          />
        )}

        <div className="photo-strip">
        {capturedPhotos.map((photo, index) => (
          <img
            key={index}
            src={photo}
            alt={`Captured ${index + 1}`}
            className="photo-thumbnail"
          />
        ))}
      </div>
      </>
    )}

    {screen === "balloon" && (
      <BalloonPopper
        sessionId={sessionId}
        onGameEnd={async () => {
        console.log("🎈 Balloon finished → preparing ad");
        
        setAdTriggered(true);
        setIsRunning(false);
        hasTriggeredRef.current = true;

        fetchFinalPrediction();
      }}
      />
    )}

    {/* Returning popup stays as-is */}
    {showReturningPopup && (
      <div className="popup-overlay">
        <div className="popup-card">
          <h2>Welcome Back!</h2>
          <p>
            Welcome back! <br />

            {daysSinceLastVisit === 0 && (
              <>We saw you earlier today.</>
            )}

            {daysSinceLastVisit === 1 && (
              <>We saw you yesterday.</>
            )}

            {daysSinceLastVisit > 1 && (
              <>We last saw you {daysSinceLastVisit} days ago.</>
            )}

            <br />
            This is your visit #{visitCount}.
          </p>
          {similarityDebug && (
            <div className="similarity-debug">
              <h4>AI Detection Details</h4>

              <div>Cosine Similarity: {similarityDebug.cosine?.toFixed(3)}</div>
              <div>Face Quality Score: {similarityDebug.quality?.toFixed(3)}</div>
              <div>Temporal Weight: {similarityDebug.temporal?.toFixed(3)}</div>
              <div>Final Similarity: {similarityDebug.final?.toFixed(3)}</div>
            </div>
          )}
          <button className="btn" onClick={confirmReturningStart}>
            Start Playing
          </button>
        </div>
      </div>
    )}

    {/* Final popup stays as-is (but Close returns to idle) */}
    {showAdPopup && (
      <div className="popup-overlay">
        <div className="popup-card">
          <h2>Just For You</h2>

          {finalAdImage ? (
            <img src={finalAdImage} alt="Ad" className="popup-ad" />
          ) : (
            <p>No advertisement available.</p>
          )}

          <p><b>Detected:</b> {finalAge}, {finalGender}</p>

          <div className="popup-buttons">
            <button
              className="btn"
              onClick={() => {
                setShowAdPopup(false);
                setScreen("idle");
                setExperience(null);
              }}
            >
              Close
            </button>

            <button
              className="btn"
              onClick={() => {
                setShowAdPopup(false);
                startGame(experience);
              }}
            >
              Play Again
            </button>
          </div>
        </div>
      </div>
    )}

  </div>
);
}


export default PhotoBooth;