// balloon-game/src/BalloonGame.jsx
import React, { useRef, useEffect, useState } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import "./BalloonGame.css";
import MassAudience from "./MassAudience";
import "./MassAudience.css";

function BalloonGame() {
  const canvasRef = useRef(null);
  const webcamRef = useRef(null);
  const balloons = useRef([]);

  const [score, setScore] = useState(0);
  const [timer, setTimer] = useState(60);
  const [isRunning, setIsRunning] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const [finalAge, setFinalAge] = useState(null);
  const [finalGender, setFinalGender] = useState(null);
  const [finalAdImage, setFinalAdImage] = useState(null);
  const [showAdPopup, setShowAdPopup] = useState(false);

  const [visitorType, setVisitorType] = useState(null);
  const [visitCount, setVisitCount] = useState(null);
  const [showReturningPopup, setShowReturningPopup] = useState(false);

  const [videoDevices, setVideoDevices] = useState([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState(null);
  const popSoundRef = useRef(null);

  const [massAdImage, setMassAdImage] = useState(null);

  useEffect(() => {
    popSoundRef.current = new Audio("/sounds/pop.mp3");
    popSoundRef.current.volume = 0.5;
  }, []);

  // -------------------------------
  // Create a balloon
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
    const colors = Object.keys(balloonImages);
    const color = colors[Math.floor(Math.random() * colors.length)];

    const img = new Image();
    img.src = balloonImages[color];

    return {
      x: Math.random() * 360 + 20,
      y: 600,
      radius: Math.random() * 25 + 35, // slightly bigger for photo balloons
      speed: Math.random() * 1.5 + 0.5,
      color,
      img,
    };
  };

  

  // -------------------------------
  // Start game
  // -------------------------------
  /*const startGame = async () => {
    setScore(0);
    setTimer(60);
    balloons.current = [];
    setIsRunning(true);

    setFinalAge(null);
    setFinalGender(null);
    setFinalAdImage(null);

  };*/
  /*const startGame = async () => {
    // close recommendation popup first
    setShowAdPopup(false);

    // 👋 returning customer gate
    if (visitorType === "returning") {
      setShowReturningPopup(true);
      return; // ⛔ stop here until user confirms
    }

    // start game normally
    /*setShowReturningPopup(false);
    setFinalAge(null);
    setFinalGender(null);
    setFinalAdImage(null);

    setScore(0);
    setTimer(60);
    balloons.current = [];
    setIsRunning(true);
    //setSessionId(uuidv4());

    try {
      const res = await axios.post("http://localhost:8000/start_game");

      setSessionId(res.data.session_id);
      setScore(0);
      setTimer(30);
      balloons.current = [];
      setIsRunning(true);
    } catch (err) {
      console.error("Start game error:", err);
    }
  };*/

  const startGame = async () => {
    try {
      const res = await axios.post("http://localhost:8000/start_game");

      // 👈 IMPORTANT: read backend response
      const { visitor_type, visit_count, session_id } = res.data;

      setSessionId(session_id);
      setVisitorType(visitor_type);
      setVisitCount(visit_count);

      // 🔔 SHOW POPUP IMMEDIATELY FOR RETURNING USER
      if (visitor_type === "returning") {
        setShowReturningPopup(true);
        return; // ⛔ wait for user confirmation
      }

      // start game normally for new user
      setScore(0);
      setTimer(10);
      balloons.current = [];
      setIsRunning(true);

    } catch (err) {
      console.error("Start game error:", err);
    }
  };

  /*if (visitorType === "returning") {
    setShowReturningPopup(true);
  }*/

  // -------------------------------
  // Game timer
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

  useEffect(() => {
    navigator.mediaDevices.enumerateDevices().then((devices) => {
      const cams = devices.filter((d) => d.kind === "videoinput");
      setVideoDevices(cams);

      // 🔥 Prefer external webcam automatically
      const externalCam =
        cams.find((c) => !c.label.toLowerCase().includes("facetime")) ||
        cams[0];

      if (externalCam) {
        setSelectedDeviceId(externalCam.deviceId);
      }
    });
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

  // -------------------------------
  // On click pop balloon
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

        // play pop sound
        if (popSoundRef.current) {
          popSoundRef.current.currentTime = 0;
          popSoundRef.current.play();
        }

        balloons.current = balloons.current.filter((b) => b !== balloon);
      }
    });
  };

  // -------------------------------
  // Send frames to backend
  // -------------------------------
  const sendFrameToBackend = async (image) => {
    try {
      if (!sessionId) return; // ⛔ safety check

      await axios.post("http://localhost:8000/upload_frame", {
        image: image,
        session_id: sessionId
      });
    } catch (err) {
      console.error("Error sending frame:", err);
    }
  };

  useEffect(() => {
    if (!isRunning) return;

    const interval = setInterval(() => {
      if (webcamRef.current) {
        const shot = webcamRef.current.getScreenshot();
        if (shot) sendFrameToBackend(shot);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isRunning]);

  // -------------------------------
  // Poll session state for returning popup during game
  // -------------------------------
  useEffect(() => {
    if (!isRunning || !sessionId) return;

    const pollInterval = setInterval(async () => {
      try {
        const res = await axios.get("http://localhost:8000/session_state");
        const { visitor_type, visit_count } = res.data;

        // If backend identified a returning customer, show popup and pause game
        if (visitor_type === "returning" && !showReturningPopup) {
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
  }, [isRunning, sessionId, showReturningPopup]);

  // -------------------------------
  // Final prediction + Update DB
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

    setShowAdPopup(true);
  } catch (err) {
    console.error("Final prediction error:", err);
  }
};


  // -------------------------------
  // UI
  // -------------------------------
  return (
    <div className="layout-container">

      {/* 🔵 WELCOME BACK POPUP */}
      {showReturningPopup && (
        <div className="popup-overlay">
          <div className="popup-card">
            <h2>Welcome Back!</h2>
            <p>
              Welcome back! <br />
              This is your visit #{visitCount}.
            </p>

            <button
              className="btn"
              onClick={() => {
                setShowReturningPopup(false);

                // actually start the game now
                setScore(0);
                setTimer(30);
                balloons.current = [];
                setIsRunning(true);
              }}
            >
              Start Playing
            </button>
          </div>
        </div>
      )}

      {/* LEFT PANEL — GAME */}
      <div className="left-panel">
        <div className="game-wrapper">
          <div className="game-card">
            <div className="top-bar">
              <h1 className="title">Balloon Popper</h1>

              <div className="score-timer">
                <div className="score-box">🎯 {score}</div>
                <div className="timer-box">⏱ {timer}s</div>
              </div>
            </div>

            <div className="game-area">
              <div className="webcam-box">
                <h3>Your Camera</h3>
                {/*<Webcam
                  audio={false}
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  width={200}
                  height={150}
                  className="webcam-frame"
                />*/}
              
                <Webcam
                  audio={false}
                  ref={webcamRef}
                  screenshotFormat="image/jpeg"
                  width={320}
                  height={240}
                  className="webcam-frame"
                  videoConstraints={{
                    /*deviceId: selectedDeviceId ? { exact: selectedDeviceId } : undefined,*/
                    facingMode: "user",
                    width: 1280,
                    height: 720
                  }}
                />

              </div>

              <canvas
                ref={canvasRef}
                width={550}
                height={700}
                onClick={handleClick}
                className="game-canvas"
              />
            </div>

            {!isRunning && {/*timer === 60*/} && (
              <button className="btn start-btn" onClick={startGame}>
                Start Game
              </button>
            )}
          </div>
        </div>
      </div>

      {/* RIGHT PANEL — MASS AUDIENCE AD */}
      <div className="right-panel">
        <MassAudience isGameRunning={isRunning} />
      </div>

      {/* FINAL INDIVIDUAL POPUP */}
      {showAdPopup && (
        <div className="popup-overlay">
          <div className="popup-card">
            <h2>Recommended For You</h2>

            {finalAdImage ? (
              <img src={finalAdImage} alt="Ad" className="popup-ad" />
            ) : (
              <p>No advertisement available.</p>
            )}

            <p><b>Score:</b> {score}</p>
          <p><b>Detected:</b> {finalAge}, {finalGender}</p>
            {/*<p><b>Detected:</b> 20-35, female</p>*/}

            <button className="btn" onClick={() => setShowAdPopup(false)}>
              Close
            </button>
            <button
              className="btn"
              onClick={() => {
                setShowAdPopup(false);   // ✅ close ad popup first
                startGame();             // then start new session
              }}
            >
              Play Again
            </button>

          </div>
        </div>
      )}
    </div>
  );
}

export default BalloonGame;

