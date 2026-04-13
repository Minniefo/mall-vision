import React, { useRef } from "react";
import Webcam from "react-webcam";
import axios from "axios";

export default function ReturningCheck() {
  const webcamRef = useRef(null);

  const check = async () => {
    const shot = webcamRef.current.getScreenshot();
    if (!shot) return;

    const res = await axios.post(
      `${import.meta.env.VITE_API_URL || "http://localhost:8000"}/check_returning_customer`,
      { image: shot }
    );

    alert(JSON.stringify(res.data, null, 2));
  };

  return (
    <div>
      <h2>Returning Customer Test</h2>
      <Webcam
        ref={webcamRef}
        audio={false}
        screenshotFormat="image/jpeg"
        width={200}
      />
      <button onClick={check}>Check Returning Customer</button>
    </div>
  );
}
