
from dotenv import load_dotenv #type: ignore
load_dotenv() # this will load all env variables

# fast api web server
from fastapi import FastAPI, WebSocket,UploadFile, File # type: ignore
from fastapi.middleware.cors import CORSMiddleware # type: ignore
from core.model_loader import ModelLoader
from websocket.live_ws import live_websocket_endpoint #type: ignore
from websocket.upload_ws import upload_websocket_endpoint #type: ignore
import shutil
import os
import asyncio

from services.video_processor import process_video

app = FastAPI(title = "AI Theft Detection and Surveillance System Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:8080"], # vite-react default port
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

@app.on_event("startup")
def startup_event():
    print("Starting Backend...")
    ModelLoader.load_models()

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket): 
    await live_websocket_endpoint(websocket)

@app.websocket("/ws/upload")
async def websocket_upload(websocket: WebSocket):
    await upload_websocket_endpoint(websocket)

@app.get("/")
def root():
    return {"message" : "Backend running succesfully !"}

@app.post("/upload-video")
async def upload_video(file: UploadFile = File(...), user_id: str = "", source_type: str = ""):

    os.makedirs("storage/videos", exist_ok=True)

    save_path = f"storage/videos/{file.filename}"

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Start processing
    asyncio.create_task(process_video(save_path, user_id, source_type))

    return {"message": "Video uploaded"}

@app.get("/health")
def health_check():
    return {"status" : "healthy"}