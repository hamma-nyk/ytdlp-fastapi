from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import ffmpeg
import os
import uuid
import threading
import time
import requests
from fastapi.middleware.cors import CORSMiddleware

origins = [
    "*",  # bisa diganti jadi spesifik: ["https://myytapp.vercel.app"]
]

# === Direktori download ===
OUTPUT_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Inisialisasi FastAPI ===
app = FastAPI(title="🎬 YouTube Converter API")
app.mount("/downloads", StaticFiles(directory=OUTPUT_DIR), name="downloads")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === ROUTE UTAMA ===
@app.get("/")
async def root():
    return JSONResponse({"status": "success", "message": "🎬 YouTube Converter API aktif"}, status_code=200)

# === AUDIO CONVERTER ===
@app.get("/convert/audio")
async def convert_audio(url: str = Query(..., description="URL YouTube")):
    try:
        file_name = f"{uuid.uuid4()}.webm"
        temp_file = os.path.join(OUTPUT_DIR, file_name)
        output_file = temp_file.replace(".webm", ".mp3")

        # Unduh audio menggunakan yt-dlp
        ydl_opts = {
            'cookiefile': 'cookies.txt',  # opsional, hapus jika tidak perlu
            "format": "bestaudio/best",
            "outtmpl": temp_file,
            "quiet": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio").replace("/", "_")

        # Konversi ke MP3
        (
            ffmpeg
            .input(temp_file)
            .output(output_file, format="mp3", acodec="libmp3lame", audio_bitrate="192k")
            .overwrite_output()
            .run(quiet=True)
        )

        os.remove(temp_file)
        file_url = f"/downloads/{os.path.basename(output_file)}"

        return JSONResponse({
            "status": "success",
            "title": title,
            "url": file_url
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# === VIDEO CONVERTER ===
@app.get("/convert/video")
async def convert_video(url: str = Query(..., description="URL YouTube")):
    try:
        file_name = f"{uuid.uuid4()}.webm"
        temp_file = os.path.join(OUTPUT_DIR, file_name)
        output_file = temp_file.replace(".webm", ".mp4")

        ydl_opts = {
            'cookiefile': 'cookies.txt',  # opsional
            "format": "bestvideo+bestaudio/best",
            "outtmpl": temp_file,
            "quiet": True,
            "merge_output_format": "webm",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video").replace("/", "_")

        # Konversi ke MP4
        (
            ffmpeg
            .input(temp_file)
            .output(output_file, format="mp4", vcodec="libx264", acodec="aac")
            .overwrite_output()
            .run(quiet=True)
        )

        os.remove(temp_file)
        file_url = f"/downloads/{os.path.basename(output_file)}"

        return JSONResponse({
            "status": "success",
            "title": title,
            "url": file_url
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === AUTO DELETE FILE SETIAP 30 MENIT ===
def auto_clean():
    while True:
        now = time.time()
        for f in os.listdir(OUTPUT_DIR):
            path = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > 1800:  # 1800 detik = 30 menit
                try:
                    os.remove(path)
                    print(f"🗑️ Deleted old file: {f}")
                except Exception as e:
                    print(f"⚠️ Gagal hapus {f}: {e}")
        time.sleep(300)  # cek setiap 5 menit

# === AUTO KEEP-ALIVE UNTUK MENCEGAH SLEEP DI RENDER ===
def keep_alive():
    while True:
        try:
            requests.get("https://ytdlp-fastapi-q05w.onrender.com/")  # ganti URL kamu di sini
            print("🔄 Keep-alive ping sent")
        except:
            print("⚠️ Gagal ping")
        time.sleep(300)  # setiap 5 menit

# === JALANKAN THREADS OTOMATIS ===
threading.Thread(target=auto_clean, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()

# # === UNTUK LOCAL TESTING ===
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
