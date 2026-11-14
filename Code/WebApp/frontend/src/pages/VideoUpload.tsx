import { useState, useCallback, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Upload, FileVideo, X, AlertCircle } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";

const MAX_FILE_SIZE = 100 * 1024 * 1024;
const ACCEPTED_TYPES = [
  "video/mp4",
  "video/avi",
  "video/x-msvideo",
  "video/quicktime",
  "video/webm",
];

const VideoUpload = () => {
  const { user } = useAuth();
  const { toast } = useToast();

  const wsRef = useRef<WebSocket | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("");
  const [progress, setProgress] = useState(0);
  const [processedFrame, setProcessedFrame] = useState<string | null>(null);

  const handleFile = (f: File) => {
    if (!ACCEPTED_TYPES.includes(f.type)) {
      toast({
        title: "Invalid file type",
        description: "Upload MP4, AVI, MOV or WebM",
        variant: "destructive",
      });
      return;
    }

    if (f.size > MAX_FILE_SIZE) {
      toast({
        title: "File too large",
        description: "Max size 100MB",
        variant: "destructive",
      });
      return;
    }

    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);

    if (e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  }, []);

  const handleBoxClick = () => {
    if (!file && !uploading) {
      fileInputRef.current?.click();
    }
  };

  const handleUpload = async () => {
    if (!file || !user) return;

    // reset frame and progress when a new upload starts
    setProcessedFrame(null);
    setProgress(0);

    setUploading(true);
    setProgress(5);
    setStatus("Uploading video...");

    wsRef.current = new WebSocket(
      `ws://127.0.0.1:8000/ws/upload?user_id=${user.id}`
    );

    await new Promise<void>((resolve, reject) => {
      wsRef.current!.onopen = () => resolve();
      wsRef.current!.onerror = () => reject(new Error("WebSocket failed"));
    });

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.progress !== undefined) {
        setProgress(data.progress);
        setStatus("Processing video...");
      }

      if (data.frame) {
        setProcessedFrame(`data:image/jpeg;base64,${data.frame}`);
      }

      if (data.status === "completed") {
        setProgress(100);
        setStatus("Processing Completed");

        toast({
          title: "Processing Completed",
          description: "Video analyzed successfully",
        });

        setUploading(false);
        setFile(null);
      }
    };

    try {
      const formData = new FormData();
      formData.append("file", file);

      await fetch(
        `http://127.0.0.1:8000/upload-video?user_id=${user.id}&source_type=uploaded_video`,
        {
          method: "POST",
          body: formData,
        }
      );

      setProgress(20);
    } catch (error) {
      toast({
        title: "Upload Failed",
        description: "Error uploading video",
        variant: "destructive",
      });

      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold">Upload Video</h1>

      <Card>
        <CardContent className="pt-6">

          {/* Hidden file input */}
          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
          />

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={handleBoxClick}
            className={`flex flex-col items-center justify-center border-2 border-dashed rounded-lg p-10 transition-colors
              ${dragOver ? "border-primary bg-primary/5" : "border-border"}
              ${!file && !uploading ? "cursor-pointer hover:border-primary/60 hover:bg-muted/40" : "cursor-default"}
            `}
          >
            {file ? (
              <div className="flex items-center gap-3">
                <FileVideo className="h-8 w-8 text-primary" />

                <div>
                  <p className="font-medium">{file.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                </div>

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setFile(null);
                  }}
                >
                  <X className="h-5 w-5 text-muted-foreground hover:text-white transition-colors" />
                </button>
              </div>
            ) : (
              <>
                <Upload className="h-10 w-10 mb-3 text-muted-foreground" />
                <p className="font-medium">Drag & Drop or Click to Upload</p>
                <p className="text-sm text-muted-foreground mt-1">
                  MP4, AVI, MOV, WebM — max 100MB
                </p>
              </>
            )}
          </div>

          {uploading && (
            <div className="mt-4 space-y-2">
              <Progress value={progress} />
              <p className="text-sm text-muted-foreground">{status}</p>
            </div>
          )}

          <div className="mt-4">
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              className="w-full"
            >
              {uploading ? "Processing..." : "Upload & Analyze"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Processed frame preview — appears once backend starts sending frames */}
      {processedFrame && (
        <Card className="border-border/50">
          <CardHeader>
            <CardTitle>Processing Preview</CardTitle>
            <CardDescription>
              Video being analyzed by AI
            </CardDescription>
          </CardHeader>
          <CardContent>
            <img
              src={processedFrame}
              className="w-full rounded-lg transition-all"
              alt="Processed video frame"
            />
          </CardContent>
        </Card>
      )}

      <Card className="border-yellow-500/40">
        <CardContent className="flex gap-3 pt-6">
          <AlertCircle className="text-yellow-400" />

          <div className="text-sm">
            <p className="font-medium text-yellow-400">
              Video Analysis
            </p>

            <p className="text-muted-foreground">
              Upload video to detect suspicious behaviour
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default VideoUpload;