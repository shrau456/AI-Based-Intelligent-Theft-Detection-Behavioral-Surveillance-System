import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import type { Tables } from "@/integrations/supabase/types";

type Detection = Tables<"detections">;
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { History, Filter, Image } from "lucide-react";
import { format } from "date-fns";

const DetectionHistory = () => {
  const { user } = useAuth();
  const [sourceFilter, setSourceFilter] = useState<string>("all");

  const [selectedDetection, setSelectedDetection] = useState<Detection | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const { data: detections = [], isLoading, refetch } = useQuery({
    queryKey: ["detections", user?.id, sourceFilter, "filter"],
    queryFn: async (): Promise<Detection[]> => {
      let query = supabase
        .from("detections")
        .select("id,user_id,label,confidence_score,snapshot_url,source_type,timestamp,created_at,video_timestamp")
        .eq("user_id", user!.id)
        .order("timestamp", { ascending: false });

      if (sourceFilter !== "all") {
        query = query.eq("source_type", sourceFilter as "uploaded_video" | "live_feed");
      }

      const { data, error } = await query;
      if (error) throw error;
      return data as Detection[];
    },
    enabled: !!user,
  });

  useEffect(() => {
    if (user) {
      refetch();
    }
  }, [sourceFilter]);

  const [imageUrls, setImageUrls] = useState<Record<string, string>>({});
  useEffect(() => {
    const loadImages = async () => {
      const urls: Record<string, string> = {};

      for (const d of detections) {
        if (d.snapshot_url) {
          const { data } = await supabase
            .storage
            .from("snapshots")
            .createSignedUrl(d.snapshot_url, 3600);

          if (data?.signedUrl) {
            urls[d.id] = data.signedUrl;
          }
        }
      }

      setImageUrls(urls);
    };

    if (detections.length > 0) {
      loadImages();
    }
  }, [detections]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Detection History</h1>
          <p className="mt-1 text-muted-foreground">{detections.length} detections found</p>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={sourceFilter} onValueChange={(value) => setSourceFilter(value)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sources</SelectItem>
              <SelectItem value="uploaded_video">Uploaded Video</SelectItem>
              <SelectItem value="live_feed">Live Feed</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card className="border-border/50">
        <CardContent className="p-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            </div>
          ) : detections.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <History className="mb-4 h-12 w-12 text-muted-foreground/30" />
              <p className="text-lg font-medium">No detections yet</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Upload a video or start a live feed to begin detecting suspicious activity.
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Snapshot</TableHead>
                  <TableHead>Confidence</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Video Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {detections.map((d) => (
                  <TableRow key={d.id}>
                    <TableCell>
                      {imageUrls[d.id] ? (
                        <img
                          src={imageUrls[d.id]}
                          alt="Snapshot"
                          className="h-10 w-14 rounded object-cover cursor-pointer hover:scale-105 transition"
                          onClick={() => {
                            setSelectedDetection(d);
                            setIsModalOpen(true);
                          }}
                        />
                      ) : (
                        <div className="flex h-10 w-14 items-center justify-center rounded bg-muted">
                          <Image className="h-4 w-4 text-muted-foreground" />
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      {d.confidence_score != null ? `${(d.confidence_score * 100).toFixed(1)}%` : "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={d.source_type === "live_feed" ? "default" : "secondary"}>
                        {d.source_type === "live_feed" ? "Live Feed" : "Video Upload"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {format(new Date(d.timestamp), "MMM d, yyyy HH:mm")}
                    </TableCell>
                    <TableCell>
                      {d.video_timestamp ? d.video_timestamp : "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Modal */}
      {isModalOpen && selectedDetection && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
          onClick={() => setIsModalOpen(false)}
        >
          <div
            className="bg-card rounded-2xl shadow-2xl max-w-3xl w-full p-6 relative"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close Button */}
            <button
              className="absolute right-4 top-4 text-muted-foreground hover:text-white"
              onClick={() => setIsModalOpen(false)}
            >
              ✕
            </button>

            {/* Title */}
            <h2 className="text-xl font-semibold mb-4">
              Suspicious Detection
            </h2>

            {/* Image — uses signed URL, not raw snapshot_url */}
            <div className="rounded-lg overflow-hidden mb-4">
              {imageUrls[selectedDetection.id] ? (
                <img
                  src={imageUrls[selectedDetection.id]}
                  alt="Detection snapshot"
                  className="w-full max-h-[500px] object-contain"
                />
              ) : (
                <div className="flex h-48 items-center justify-center rounded-lg bg-muted">
                  <Image className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
            </div>

            {/* Details */}
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Confidence</p>
                <p className="font-medium">
                  {selectedDetection.confidence_score != null
                    ? `${(selectedDetection.confidence_score * 100).toFixed(1)}%`
                    : "—"}
                </p>
              </div>

              <div>
                <p className="text-muted-foreground">Source</p>
                <p className="font-medium">
                  {selectedDetection.source_type === "live_feed" ? "Live Feed" : "Video Upload"}
                </p>
              </div>

              <div>
                <p className="text-muted-foreground">Time</p>
                <p className="font-medium">
                  {format(new Date(selectedDetection.timestamp), "MMM d, yyyy HH:mm:ss")}
                </p>
              </div>

              <div>
                <p className="text-muted-foreground">Video Timestamp</p>
                <p className="font-medium">
                  {selectedDetection.video_timestamp || "—"}
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default DetectionHistory;

