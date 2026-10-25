import yt_dlp
ydl_opts = {
    "format": "bestaudio/best",
    "quiet": False,
    "no_warnings": False,
}
try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download(["https://www.youtube.com/watch?v=3LRZRSIh_KE"])
except Exception as e:
    print("ERROR:", e)
