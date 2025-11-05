from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import yt_dlp
import ffmpeg
import os
import uuid
import threading
import time
import requests


# === Direktori download ===
OUTPUT_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === Inisialisasi FastAPI ===
app = FastAPI(title="🎬 Lightweight YouTube Converter API")
app.mount("/downloads", StaticFiles(directory=OUTPUT_DIR), name="downloads")

# === CORS ===
origins = ["*"] # bisa diganti jadi spesifik: ["https://myytapp.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === Variabel global untuk kontrol aktivitas ===
last_active = time.time()

def mark_active():
    global last_active
    last_active = time.time()
    
# === ROUTE UTAMA ===
@app.get("/")
async def root():
    return JSONResponse({"status": "success", "message": "🎬 Lightweight YouTube Converter API aktif"}, status_code=200)

# === AUDIO CONVERTER ===
@app.get("/convert/audio")
async def convert_audio(url: str = Query(..., description="URL YouTube")):
    mark_active()
    try:
        file_name = f"{uuid.uuid4()}.webm"
        temp_file = os.path.join(OUTPUT_DIR, file_name)
        output_file = temp_file.replace(".webm", ".mp3")

        # Unduh audio menggunakan yt-dlp
        ydl_opts = {
            'cookiefile': 'cookies.txt',  # opsional, hapus jika tidak perlu
            "format": "bestaudio[ext=webm]/bestaudio/best",
            "outtmpl": temp_file,
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "skip_download": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "audio").replace("/", "_")

        # Konversi ke MP3
        (
            ffmpeg
            .input(temp_file)
            .output(output_file,
                    format="mp3",
                    acodec="libmp3lame",
                    audio_bitrate="128k",
                    preset="ultrafast",
                    threads=1)
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
    mark_active()
    try:
        file_name = f"{uuid.uuid4()}.webm"
        temp_file = os.path.join(OUTPUT_DIR, file_name)
        output_file = temp_file.replace(".webm", ".mp4")

        ydl_opts = {
            'cookiefile': 'cookies.txt',  # opsional
            "format": "bestvideo[height<=480]+bestaudio/best",  # maksimal 480p (hemat bandwidth)
            "outtmpl": temp_file,
            "quiet": True,
            "merge_output_format": "webm",
            "noplaylist": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "geo_bypass": True,
            "skip_download": False,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video").replace("/", "_")

        # Konversi ke MP4
        (
            ffmpeg
            .input(temp_file)
            .output(output_file,
                    format="mp4",
                    vcodec="libx264",
                    acodec="aac",
                    preset="ultrafast",   # CPU rendah
                    crf=32,               # kualitas lebih kecil ukuran
                    threads=1)
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

@app.get("/downloads/{filename}")
async def download_file(filename: str):
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return JSONResponse({"error": "File not found"}, status_code=404)
    
    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=filename,  # paksa browser download
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
    
# === AUTO DELETE FILE SETIAP 30 MENIT ===
def auto_clean():
    while True:
        now = time.time()
        for f in os.listdir(OUTPUT_DIR):
            path = os.path.join(OUTPUT_DIR, f)
            if os.path.isfile(path) and now - os.path.getmtime(path) > 1800:
                try:
                    os.remove(path)
                    print(f"🗑️ Deleted old file: {f}")
                except Exception as e:
                    print(f"⚠️ Gagal hapus {f}: {e}")
        time.sleep(600)  # cek tiap 5 menit

# === SMART KEEP-ALIVE ===
def keep_alive():
    global last_active
    url = "https://ytdlp-fastapi-q05w.onrender.com/"  # ganti dengan URL render kamu
    while True:
        # Kalau aktif dalam 15 menit terakhir → kirim ping
        if time.time() - last_active < 900:
            try:
                requests.get(url)
                print("🔄 Keep-alive ping sent (active)")
            except Exception as e:
                print("⚠️ Gagal ping:", e)
        else:
            print("💤 Idle mode, skip ping (biar hemat jam).")
        time.sleep(300)

# === JALANKAN THREADS OTOMATIS ===
threading.Thread(target=auto_clean, daemon=True).start()
threading.Thread(target=keep_alive, daemon=True).start()

# === UNTUK LOCAL TESTING ===
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)
