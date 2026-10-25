from youtube_transcript_api import YouTubeTranscriptApi
api = YouTubeTranscriptApi()
transcript_list = api.list("u6XAPnuFjJc")
t = transcript_list.find_transcript(["en"])
fetched = t.translate('de').fetch()
print(type(fetched))
try:
    print(hasattr(fetched, 'snippets'))
except Exception as e:
    print(e)
