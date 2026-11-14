import { useState, useRef, useCallback, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth"; // this needs to added inorder to get user_id
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Camera, Square, Circle } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

const LiveFeed = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const [isStreaming, setIsStreaming] = useState(false);
  const [processedFrame, setProcessedFrame] = useState<string | null>(null);

  const { toast } = useToast();

  // getting user 
  const { user } = useAuth();

  const startCamera = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: 640, height: 480 },
      audio: false,
    });

    if (!videoRef.current) return;

    videoRef.current.srcObject = stream;
    await videoRef.current.play(); // FORCE PLAY

    wsRef.current = new WebSocket(`ws://127.0.0.1:8000/ws/live?user_id=${user?.id || "unknown"}&source_type=live_feed`);
    // here we are passing user_id from the frontend, so this same id is also used by the backend for the reporting purpose

    const sendFrame = () => {
      if (!videoRef.current || !canvasRef.current || !wsRef.current) return;

      const video = videoRef.current;

      // Wait until video fully ready
      if (video.readyState !== 4 || video.videoWidth === 0) {
        requestAnimationFrame(sendFrame);
        return;
      }

      const canvas = canvasRef.current;
      const ctx = canvas.getContext("2d");

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      ctx?.drawImage(video, 0, 0);

      const base64Image = canvas.toDataURL("image/jpeg", 0.6);

      if (wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(base64Image);
      }
    };

    wsRef.current.onopen = () => {
      console.log("WebSocket Connected");
      toast({ title: "ML Connected", description: "Live AI detection started." });

      sendFrame(); // START LOOP HERE
    };

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setProcessedFrame(data.frame);

      if (data.events.length > 0) {
        console.log("Suspicious Event:", data.events);
      }

      sendFrame(); // request-response loop
    };

    wsRef.current.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    wsRef.current.onclose = () => {
      console.log("WebSocket closed");
    };

    setIsStreaming(true);
  }, [toast]);

  const stopCamera = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (videoRef.current?.srcObject) {
      const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
      tracks.forEach((track) => track.stop());
    }

    setIsStreaming(false);
    setProcessedFrame(null);
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">Live AI Surveillance</h1>

      <Card>
        <div className="relative aspect-video bg-black">
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{ display: "none" }}
          />

          {processedFrame && (
            <img
              src={processedFrame}
              alt="Processed"
              className="h-full w-full object-cover"
            />
          )}


          {isStreaming && (
            <div className="absolute left-4 top-4 flex items-center gap-2 rounded-full bg-red-600 px-3 py-1 text-xs text-white">
              <Circle className="h-2 w-2 fill-current animate-pulse" />
              LIVE
            </div>
          )}
        </div>

        <CardContent className="flex gap-3 pt-4">
          {!isStreaming ? (
            <Button onClick={startCamera} className="flex-1 gap-2">
              <Camera className="h-4 w-4" /> Start Surveillance
            </Button>
          ) : (
            <Button onClick={stopCamera} variant="destructive" className="flex-1 gap-2">
              <Square className="h-4 w-4" /> Stop Surveillance
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Hidden canvas for capturing frames */}
      <canvas ref={canvasRef} style={{ display: "none" }} />
    </div>
  );
};

export default LiveFeed;
