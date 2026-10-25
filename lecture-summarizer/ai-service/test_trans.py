from youtube_transcript_api import YouTubeTranscriptApi
from deep_translator import GoogleTranslator

api = YouTubeTranscriptApi()
t_list = api.list('3LRZRSIh_KE')
t = t_list.find_transcript(['hi'])
fetched = t.fetch()
text = " ".join([s['text'] if isinstance(s, dict) else s.text for s in fetched])

print("Original length:", len(text))
chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
translated_text = ""
for chunk in chunks:
    translated_text += GoogleTranslator(source='auto', target='en').translate(chunk) + " "

print("Translated snippet:", translated_text[:200])
