from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
transcript_api = YouTubeTranscriptApi()

def get_youtube_transcript(video_id: str) -> str:
    try:
        fetched = transcript_api.fetch(
            video_id,
            languages=["en", "en-US", "en-GB", "a.en"],
        )
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
    except (TranscriptsDisabled, VideoUnavailable) as e:
        raise ValueError(str(e))

    text = " ".join(snippet.text for snippet in fetched.snippets)
    if not text.strip():
        raise ValueError("YouTube transcript is empty")
    return text.strip()

print(get_youtube_transcript("3LRZRSIh_KE")[:100])
