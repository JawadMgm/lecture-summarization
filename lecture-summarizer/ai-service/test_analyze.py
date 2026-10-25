import json
from app import get_youtube_transcript, analyze_transcript

transcript = get_youtube_transcript("rfG8ce4nNh0")
print("Transcript length:", len(transcript))
res = analyze_transcript(transcript)
print(json.dumps(res, indent=2))
