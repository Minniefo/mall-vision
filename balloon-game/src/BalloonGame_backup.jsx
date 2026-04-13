import React, { useRef, useEffect, useState } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import MassAudience from "./MassAudience";
import "./BalloonGamePortrait.css";
import "./MassAudience.css";

function BalloonGame() {
  const canvasRef = useRef(null);
  const webcamRef = useRef(null);
  const balloons = useRef([]);
  const popSoundRef = useRef(null);

  const [score, setScore] = useState(0);
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
  const USE_UGREEN_CAMERA = false; 
  // true  → use UGREEN USB webcam
  // false → use laptop default webcam
  // "idle" | "game" | "result"

  // -------------------------------
  // Sound
  // -------------------------------
  useEffect(() => {
    popSoundRef.current = new Audio("/sounds/pop.mp3");
    popSoundRef.current.volume = 0.5;
  }, []);

  // -------------------------------
  // Balloon assets
  // -------------------------------
  const balloonImages = {
    red: "/balloons/1.png",
    blue: "/balloons/2.png",
    green: "/balloons/3.png",
    yellow: "/balloons/4.png",
    purple: "/balloons/5.png",
    orange: "/balloons/6.png",
  };

  const createBalloon = () => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const colors = Object.keys(balloonImages);
    const color = colors[Math.floor(Math.random() * colors.length)];

    const img = new Image();
    img.src = balloonImages[color];

    return {
      x: Math.random() * canvas.width,
      y: canvas.height + 50,
      radius: Math.random() * 30 + 40,
      speed: Math.random() * 1.5 + 0.5,
      color,
      img,
    };
  };

  // -------------------------------
  // Start game (logic unchanged)
  // -------------------------------
  const startGame = async () => {
    try {
      setScreen("game");
      // Fullscreen for kiosk feel (safe: only triggers if browser allows)
      document.documentElement.requestFullscreen?.().catch(() => {});

      const res = await axios.post("http://localhost:8000/start_game");

      const { visitor_type, visit_count, session_id, days_since_last_visit } = res.data;
      setDaysSinceLastVisit(days_since_last_visit);

      setSessionId(session_id);
      setVisitorType(visitor_type);
      setVisitCount(visit_count);

      if (visitor_type === "returning") {
        setShowReturningPopup(true);
        return;
      }

      setScore(0);
      setTimer(30);
      balloons.current = [];
      setIsRunning(true);
    } catch (err) {
      console.error("Start game error:", err);
    }
  };

  // -------------------------------
  // Timer
  // -------------------------------
  useEffect(() => {
    if (!isRunning) return;

    if (timer <= 0) {
      setIsRunning(false);
      fetchFinalPrediction();
      return;
    }

    const interval = setInterval(() => setTimer((t) => t - 1), 1000);
    return () => clearInterval(interval);
  }, [isRunning, timer]);

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
  // Balloon movement
  // -------------------------------
  useEffect(() => {
    if (!isRunning) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");

    const spawnInterval = setInterval(() => {
      balloons.current.push(createBalloon());
    }, 800);

    const update = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      balloons.current.forEach((balloon) => {
        balloon.y -= balloon.speed;

        ctx.drawImage(
          balloon.img,
          balloon.x - balloon.radius,
          balloon.y - balloon.radius,
          balloon.radius * 2,
          balloon.radius * 2
        );

        if (balloon.y + balloon.radius < 0) {
          balloons.current = balloons.current.filter((b) => b !== balloon);
        }
      });

      requestAnimationFrame(update);
    };

    update();
    return () => clearInterval(spawnInterval);
  }, [isRunning]);

  useEffect(() => {
  if (screen !== "game") return;

  const canvas = canvasRef.current;
  if (!canvas) return;

  const resizeCanvas = () => {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
  };

  resizeCanvas();
  window.addEventListener("resize", resizeCanvas);

  return () => window.removeEventListener("resize", resizeCanvas);
}, [screen]);

  // -------------------------------
  // Click to pop
  // -------------------------------
  const handleClick = (event) => {
    if (!isRunning) return;

    const rect = canvasRef.current.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    balloons.current.forEach((balloon) => {
      const dx = clickX - balloon.x;
      const dy = clickY - balloon.y;

      if (Math.sqrt(dx * dx + dy * dy) < balloon.radius) {
        setScore((s) => s + 1);

        if (popSoundRef.current) {
          popSoundRef.current.currentTime = 0;
          popSoundRef.current.play();
        }

        balloons.current = balloons.current.filter((b) => b !== balloon);
      }
    });
  };

  // -------------------------------
  // Send frames
  // -------------------------------
  const sendFrameToBackend = async (image) => {
    try {
      if (!sessionId) return;

      await axios.post("http://localhost:8000/upload_frame", {
        image,
        session_id: sessionId,
      });
    } catch (err) {
      console.error("Error sending frame:", err);
    }
  };

  useEffect(() => {
    if (!webcamRef.current) return;

    const interval = setInterval(() => {
      const shot = webcamRef.current.getScreenshot();
      if (!shot) return;

      // 🔹 If in game → send with session
      if (screen === "game" && sessionId) {
        sendFrameToBackend(shot);
      }

      // 🔹 If in idle → send MASS frame
      if (screen === "idle") {
        axios.post("http://localhost:8000/upload_frame", {
          image: shot,
          session_id: null,
        });
      }

    }, 2000);

    return () => clearInterval(interval);
  }, [screen, sessionId]);

  // -------------------------------
  // Poll session state for returning popup during game
  // -------------------------------
  useEffect(() => {
    if (screen !== "game" || !sessionId) return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get("http://localhost:8000/session_state");
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
    }, 1000); // Poll every 1 second

    return () => clearInterval(pollInterval);
  }, [screen, sessionId, showReturningPopup]);

  // -------------------------------
  const fetchFinalPrediction = async () => {
    try {
      const res = await axios.get("http://localhost:8000/final_prediction");
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
      await axios.post("http://localhost:8000/acknowledge_returning");
    } catch (e) {
      console.error("Acknowledge failed:", e);
    }
    setShowReturningPopup(false);
    setScore(0);
    setTimer(30);
    balloons.current = [];
    setIsRunning(true);
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
      <MassAudience isGameRunning={false} />
    </div>

    <div className="idle-cta">
      <button className="start-btn-modern" onClick={startGame}>
        ▶ Start Game
      </button>
    </div>

  </div>
)}

    {/* GAME SCREEN */}
    {screen === "game" && (
      <>
        {/* your existing top bar + canvas + camera + mass removed */}
        <div className="kiosk-top">
          <div className="kiosk-title">Balloon Popper</div>
          <div className="kiosk-metrics">
            <div className="metric-box">🎯 {score}</div>
            <div className="metric-box">⏱ {timer}s</div>
          </div>
        </div>

        

        <div className="camera-wrap">
          <div className="section-label">Your Camera</div>
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

        <div className="canvas-wrap">
          <canvas
            ref={canvasRef}
            onClick={handleClick}
            className="game-canvas"
          />
        </div>
      </>
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

          <p><b>Score:</b> {score}</p>
          <p><b>Detected:</b> {finalAge}, {finalGender}</p>

          <div className="popup-buttons">
            <button
              className="btn"
              onClick={() => {
                setShowAdPopup(false);
                setScreen("idle");
              }}
            >
              Close
            </button>

            <button
              className="btn"
              onClick={() => {
                setShowAdPopup(false);
                startGame();
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


export default BalloonGame;