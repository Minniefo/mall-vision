# MallVision AI Kiosk 🚀

[![Live Demo](https://img.shields.io/badge/Live-Demo-brightgreen)](http://52.202.161.100/kiosk)
[![Backend](https://img.shields.io/badge/Backend-FastAPI-blue)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-React-61dafb)](https://reactjs.org/)
[![Database](https://img.shields.io/badge/Database-MongoDB-47A248)](https://www.mongodb.com/)

**MallVision** is a next-generation AI-powered kiosk system designed for smart shopping environments. It leverages computer vision and deep learning to provide real-time audience analytics, personalized advertising, and interactive user engagement.

---

## 🔗 Live Deployment
Experience the kiosk in action: [http://52.202.161.100/](http://52.202.161.100/)

---

## ✨ Key Features

### 1. Real-time Demographic Analysis
*   **Age & Gender Detection**: High-accuracy inference using a custom CNN model with attention mechanisms.
*   **Emotion Tracking**: Detects visitor mood to refine advertisement recommendations.
*   **Mass Audience Inference**: Analyzes crowds to determine the "majority" demographic for group-level targeting.

### 2. Smart Retention System
*   **Returning Visitor Identification**: Recognizes recurring customers using anonymized face embeddings (InsightFace) and cosine similarity.
*   **Privacy First**: No PII (Personally Identifiable Information) is stored. Embeddings are salted and anonymized.
*   **Loyalty Insights**: Tracks visit frequency and time since last visit to personalize the welcome experience.

### 3. Dynamic Advertisement Engine
*   **Targeted Delivery**: Serves relevant image/video ads based on detected age, gender, and current system mode (Individual vs. Mass).
*   **Real-time Recommendations**: Integrated classifier and recommendation engine to maximize engagement.

### 4. Interactive Engagement
*   **Balloon Popper Game**: Engaging mini-game to keep visitors entertained while the system analyzes demographics.
*   **Photo Booth**: Interactive feature for visitors to capture and share moments.

### 5. Enterprise Analytics
*   **Live Dashboard**: Real-time visualization of visitor trends, demographic distributions, and ad performance.
*   **Anomaly Detection**: Proactive monitoring of system performance and detection accuracy.

---

## 🛠 Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, FastAPI, TensorFlow, Keras, OpenCV, MTCNN, YOLOv8 |
| **Frontend** | React (Vite), TailwindCSS, Chart.js, React-Webcam |
| **Database** | MongoDB Atlas |
| **DevOps** | Docker, AWS (EC2, ECR), GitHub Actions (CI/CD) |
| **ML Models** | Custom CNN (Age/Gender), InsightFace (Embeddings), YOLOv8 (Crowd) |

---

## 📂 Project Structure

```text
.
├── age-gender-backend/      # FastAPI Backend & AI Models
├── balloon-game/            # React Frontend (Kiosk & Dashboard)
├── Advertisements/          # Media repository for targeted ads
├── AWS_DEPLOYMENT.md        # Detailed guide for AWS ECR/EC2 setup
├── Model.ipynb              # Research & Model Training Notebook
└── README.md                # Project Documentation
```

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10+
*   Node.js 18+
*   MongoDB Atlas Account
*   AWS Account (for deployment)

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd age-gender-backend
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables (create a `.env` file):
   ```env
   MONGO_URI=your_mongodb_connection_string
   ```
4. Start the server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd balloon-game
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Configure API endpoint in `.env`:
   ```env
   VITE_API_URL=http://localhost:8000
   ```
4. Start the development server:
   ```bash
   npm run dev
   ```

---

## ☁️ Deployment
The project is optimized for AWS deployment using a robust CI/CD pipeline.
*   **Build**: GitHub Actions handles the heavy Docker builds (circumventing EC2 RAM limits).
*   **Registry**: Images are stored in **Amazon ECR**.
*   **Host**: Running on **Ubuntu 24.04 LTS** on **EC2 (t3.micro)** with 4GB Swap enabled.

For detailed instructions, refer to [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md).

---

## 📜 License
This project is developed for research purposes in Mall Audience Analytics.
