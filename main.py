from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import yt_dlp
import ffmpeg    
import os
import uuid

OUTPUT_DIR = "downloads"
os.makedirs(OUTPUT_DIR, exist_ok=True)
app = FastAPI(title="YouTube Converter API")
app.mount("/downloads", StaticFiles(directory=OUTPUT_DIR), name="downloads")

@app.get("/")
async def root():
    return JSONResponse({"status": "success", "message": "🎬 YouTube Converter API aktif"}, status_code=200)

@app.get("/convert/audio")
async def convert_audio(url: str = Query(..., description="URL YouTube")):
    try:
        file_name = f"{uuid.uuid4()}.webm"
        temp_file = os.path.join(OUTPUT_DIR, file_name)
        output_file = temp_file.replace(".webm", ".mp3")
        
        # Ambil info YouTube tanpa download file
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": temp_file,
            "quiet": True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_url = info["url"]
            title = info.get("title", "audio").replace("/", "_")
        
        # Convert ke MP3
        (
            ffmpeg
            .input(temp_file)
            .output(output_file, format="mp3", acodec="libmp3lame", audio_bitrate="192k")
            .overwrite_output()
            .run(quiet=True)
        )
        
        os.remove(temp_file)
        
        file_url = f"/downloads/{file_name.replace('.webm', '.mp3')}"
        return JSONResponse({"status": "success", "title": title, "direct_link": audio_url, "url": file_url}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/convert/video")
async def convert_video(url: str = Query(..., description="URL YouTube")):
    try:
        file_name = f"{uuid.uuid4()}.webm"
        temp_file = os.path.join(OUTPUT_DIR, file_name)
        output_file = temp_file.replace(".webm", ".mp4")
        
        # Ambil info YouTube tanpa download file
        ydl_opts = {
            "format": "bestvideo+bestaudio/best",
            "outtmpl": temp_file,
            "quiet": True,
            "merge_output_format": "webm",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get("title", "video").replace("/", "_")
            
        # Convert ke MP3
        (
            ffmpeg
            .input(temp_file)
            .output(output_file, format="mp4", vcodec="libx264", acodec="aac")
            .overwrite_output()
            .run(quiet=True)
            
        )
        
        os.remove(temp_file)
        
        file_url = f"/downloads/{file_name.replace('.webm', '.mp4')}"
        return JSONResponse({"status": "success", "title": title, "url": file_url}, status_code=200)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)