# Lecture Summarizer

Upload a lecture video and get AI-generated transcripts, summaries, keywords, and practice questions.

## Architecture

```
Frontend (React)  →  Backend (Express)  →  AI Service (FastAPI)
     :3000               :5001                    :8000
                              ↓
                         MongoDB
```

| Service | Role |
|---------|------|
| **Frontend** | Upload UI, status polling, results display |
| **Backend** | Video storage, MongoDB persistence, AI orchestration |
| **AI Service** | Whisper transcription, BART summarization, KeyBERT keywords |

## Prerequisites

- Node.js 18+
- Python 3.9+
- Docker (for local MongoDB)
- FFmpeg (required by MoviePy/Whisper)

Install FFmpeg on macOS:

```bash
brew install ffmpeg
```

## Setup

### 1. Start MongoDB

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
cp .env.example .env   # edit MONGO_URI if needed
npm install
npm start
```

Default env:

```
PORT=5001
MONGO_URI=mongodb://localhost:27017/lectureDB
AI_SERVICE_URL=http://localhost:8000
```

### 3. AI Service

First run downloads ML models (~1.5 GB). This can take several minutes.

```bash
cd ai-service
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### 4. Frontend

```bash
cd frontend
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000).

## Usage

1. Enter a lecture title and select a video file (with an audio track).
2. Click **Generate Notes**.
3. Wait while the AI service transcribes and analyzes the video (may take several minutes for long lectures).
4. View the summary, keywords, practice questions, and full transcript.
5. Past lectures appear in the history panel.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check (backend & AI service) |
| GET | `/api/lectures` | List all lectures |
| POST | `/api/lectures/upload` | Upload video (multipart: `video`, `title`) |
| GET | `/api/lectures/:id` | Get lecture details and processing status |
| POST | `/process-video` | AI service — process a video file |

## Troubleshooting

**Port 5000 in use (macOS)** — macOS AirPlay Receiver uses port 5000. This project defaults to **5001** to avoid conflicts.

**MongoDB connection failed** — Make sure MongoDB is running locally (`mongod`) or start it with `docker compose up -d`. Update `MONGO_URI` in `backend/.env`.

**AI service not reachable** — Start the AI service first (`python app.py` in `ai-service/`). Model loading takes time on first startup.

**Processing failed** — Ensure the video has an audio track and FFmpeg is installed.

**Slow processing** — Whisper + summarization on CPU can take 1–5× the video length. Use shorter clips for testing.
