import os
import re
import json
import glob
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
import whisper
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from moviepy import VideoFileClip

app = FastAPI(title="Lecture Summarizer AI Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOADS_DIR = "downloads"
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

WHISPER_MODEL = "base"
print(f"Loading Whisper model '{WHISPER_MODEL}'...")
whisper_model = whisper.load_model(WHISPER_MODEL)

_executor = ThreadPoolExecutor(max_workers=3)
transcript_api = YouTubeTranscriptApi()

class VideoRequest(BaseModel):
    lectureId: str
    videoPath: str

class UrlRequest(BaseModel):
    lectureId: str
    url: str

def extract_youtube_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return ""

def preprocess_transcript(text: str) -> str:
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def analyze_transcript(transcript: str) -> dict:
    cleaned_transcript = preprocess_transcript(transcript)

    if len(cleaned_transcript.split()) < 10:
        return {
            "transcript": cleaned_transcript,
            "summary": "This video's captions are too short or too noisy to build proper study notes.",
            "easyExplanation": "",
            "topicBreakdown": [],
            "importantNotes": [],
            "keyTerms": [],
            "formulas": [],
            "practiceProblems": [],
            "keywords": []
        }

    prompt = f"""You are an expert lecture summarizer.

Transcript:
{cleaned_transcript[:20000]}

---
Based on the above transcript, generate highly structured and detailed study notes.
You MUST output STRICTLY valid JSON matching EXACTLY this schema (do not add any other keys). 
For the arrays `importantNotes`, `formulas`, `practiceProblems`, and `keywords`, they MUST be arrays of STRINGS, NOT objects (e.g. `["string1", "string2"]`).
If there are no formulas or practice problems, return an empty array `[]` for those fields:
{{
  "summary": "A 1-paragraph overview.",
  "easyExplanation": "A 1-paragraph simple explanation for a beginner.",
  "topicBreakdown": [{{"title": "string", "content": "string"}}],
  "importantNotes": ["string"],
  "keyTerms": [{{"term": "string", "definition": "string"}}],
  "formulas": ["string"],
  "practiceProblems": ["string"],
  "keywords": ["string"]
}}
"""

    print("Generating notes via Local Ollama (llama3.2)...")
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "format": "json"
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        result_json = json.loads(data["response"])
        
        # Ensure schema compliance
        defaults = {
            "summary": "No summary generated.",
            "easyExplanation": "No easy explanation generated.",
            "topicBreakdown": [],
            "importantNotes": [],
            "keyTerms": [],
            "formulas": [],
            "practiceProblems": [],
            "keywords": []
        }
        for k, v in defaults.items():
            if k not in result_json:
                result_json[k] = v

        result_json["transcript"] = cleaned_transcript
        return result_json
    except Exception as e:
        print(f"Ollama API Error: {e}")
        return {
            "transcript": cleaned_transcript,
            "summary": f"Failed to generate summary with local LLM. Error: {str(e)}",
            "easyExplanation": "",
            "topicBreakdown": [],
            "importantNotes": [],
            "keyTerms": [],
            "formulas": [],
            "practiceProblems": [],
            "keywords": []
        }

def get_youtube_transcript(video_id: str) -> str:
    try:
        fetched = transcript_api.fetch(video_id, languages=["en", "en-US", "en-GB", "a.en"])
    except NoTranscriptFound:
        try:
            transcript_list = transcript_api.list(video_id)
            for t in transcript_list:
                if t.is_translatable:
                    fetched = t.translate('en').fetch()
                    break
            else:
                raise ValueError("No translatable transcripts found.")
        except Exception as e:
            raise ValueError(str(e))
    except Exception as e:
        raise ValueError(str(e))

    text = " ".join(snippet.text for snippet in fetched.snippets)
    if not text.strip():
        raise ValueError("YouTube transcript is empty")
    return text.strip()

def transcribe_audio(audio_path: str) -> str:
    print(f"Transcribing audio with Whisper {WHISPER_MODEL}...")
    result = whisper_model.transcribe(
        audio_path,
        fp16=False,
        language="en",
        beam_size=1,
        best_of=1,
        condition_on_previous_text=False,
    )
    return result["text"].strip()

def analyze_video(video_path: str, lecture_id: str) -> dict:
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")

    audio_path = f"temp_audio_{lecture_id}.wav"
    try:
        video = VideoFileClip(video_path)
        if video.audio is None:
            raise HTTPException(status_code=400, detail="Video has no audio track")

        video.audio.write_audiofile(audio_path, logger=None)
        video.close()

        transcript = transcribe_audio(audio_path)
        return analyze_transcript(transcript)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

def download_video(url: str, lecture_id: str) -> str:
    output_template = os.path.join(DOWNLOADS_DIR, f"{lecture_id}.%(ext)s")
    ydl_opts_list = [
        {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android"]}},
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }],
        }
    ]

    last_error = None
    for ydl_opts in ydl_opts_list:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            matches = glob.glob(os.path.join(DOWNLOADS_DIR, f"{lecture_id}.*"))
            if matches:
                return matches[0]
        except Exception as e:
            last_error = e
            for f in glob.glob(os.path.join(DOWNLOADS_DIR, f"{lecture_id}.*")):
                try: os.remove(f)
                except: pass

    raise HTTPException(status_code=400, detail=f"Could not download video: {last_error}")

def process_url_sync(lecture_id: str, url: str) -> dict:
    downloaded_path = None
    try:
        youtube_id = extract_youtube_id(url)
        if youtube_id:
            print(f"Fetching YouTube captions for {youtube_id}...")
            try:
                transcript = get_youtube_transcript(youtube_id)
                return analyze_transcript(transcript)
            except Exception as e:
                print(f"Failed to fetch YouTube captions via API ({e}). Falling back to audio download...")

        print("Downloading video audio...")
        downloaded_path = download_video(url, lecture_id)

        if downloaded_path.endswith((".mp3", ".wav", ".m4a", ".ogg")):
            transcript = transcribe_audio(downloaded_path)
            return analyze_transcript(transcript)

        return analyze_video(downloaded_path, lecture_id)
    finally:
        if downloaded_path and os.path.exists(downloaded_path):
            try: os.remove(downloaded_path)
            except: pass

def process_video_sync(video_path: str, lecture_id: str) -> dict:
    return analyze_video(video_path, lecture_id)

@app.get("/health")
async def health():
    return {"status": "ok", "whisperModel": WHISPER_MODEL}

@app.post("/process-video")
async def process_video(request: VideoRequest):
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, lambda: process_video_sync(request.videoPath, request.lectureId))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-url")
async def process_url(request: UrlRequest):
    try:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, lambda: process_url_sync(request.lectureId, request.url))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
