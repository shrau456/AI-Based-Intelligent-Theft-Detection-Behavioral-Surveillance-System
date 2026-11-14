import { Link } from "react-router-dom";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Video, Camera, History, Shield } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid
} from "recharts";

const Dashboard = () => {
  const { user } = useAuth();

  const { data: detectionCount = 0 } = useQuery({
    queryKey: ["detectionCount", user?.id],
    queryFn: async () => {
      const { count } = await supabase
        .from("detections")
        .select("*", { count: "exact", head: true })
        .eq("user_id", user!.id);
      return count ?? 0;
    },
    enabled: !!user,
  });

  // Live feed detections
  const { data: liveCount = 0 } = useQuery({
    queryKey: ["liveCount", user?.id],
    queryFn: async () => {
      const { count } = await supabase
        .from("detections")
        .select("*", { count: "exact", head: true })
        .eq("user_id", user!.id)
        .eq("source_type", "live_feed");

      return count ?? 0;
    },
    enabled: !!user,
  });

  // Uploaded video detections
  const { data: uploadCount = 0 } = useQuery({
    queryKey: ["uploadCount", user?.id],
    queryFn: async () => {
      const { count } = await supabase
        .from("detections")
        .select("*", { count: "exact", head: true })
        .eq("user_id", user!.id)
        .eq("source_type", "uploaded_video");

      return count ?? 0;
    },
    enabled: !!user,
  });

  // Average confidence
  const { data: avgConfidence = 0 } = useQuery({
    queryKey: ["avgConfidence", user?.id],
    queryFn: async () => {
      const { data } = await supabase
        .from("detections")
        .select("confidence_score")
        .eq("user_id", user!.id);

      if (!data || data.length === 0) return 0;

      const avg =
        data.reduce((sum, d) => sum + (d.confidence_score || 0), 0) /
        data.length;

      return avg;
    },
    enabled: !!user,
  });

  const { data: trendData = [] } = useQuery({
    queryKey: ["trendData", user?.id],
    queryFn: async () => {
      const { data } = await supabase
        .from("detections")
        .select("timestamp")
        .eq("user_id", user!.id)
        .order("timestamp", { ascending: true });

      if (!data) return [];

      const grouped: Record<string, number> = {};

      data.forEach((d) => {
        const date = new Date(d.timestamp).toLocaleDateString();

        grouped[date] = (grouped[date] || 0) + 1;
      });

      return Object.entries(grouped).map(([date, count]) => ({
        date,
        count,
      }));
    },
    enabled: !!user,
  });

  const { data: profile } = useQuery({
    queryKey: ["profile", user?.id],
    queryFn: async () => {
      const { data } = await supabase
        .from("profiles")
        .select("*")
        .eq("user_id", user!.id)
        .maybeSingle();
      return data;
    },
    enabled: !!user,
  });

  // Ping backend /health every 10 seconds to check if its health/alive
  const { data : backendOnline = false } = useQuery({
    queryKey: ["backendHealth"],
    queryFn: async () => {
      try {
        const res = fetch("http://127.0.0.1:8000/health", {
          signal: AbortSignal.timeout(3000), // 3 second timeout
        });
        return (await res).ok;
      } catch {
        return false;
      }
    } ,
    refetchInterval: 30000 // re-fetch after every 10 seconds
  })

  const actions = [
    {
      to: "/dashboard/upload",
      icon: Video,
      title: "Upload Video",
      description: "Upload a video file for AI analysis and suspicious activity detection",
      color: "text-blue-400",
    },
    {
      to: "/dashboard/live",
      icon: Camera,
      title: "Live Camera Feed",
      description: "Start real-time surveillance using your camera with AI detection",
      color: "text-emerald-400",
    },
    {
      to: "/dashboard/history",
      icon: History,
      title: "Detection History",
      description: `View past detections (${detectionCount} total)`,
      color: "text-amber-400",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">
          Welcome back, {profile?.display_name || "Agent"}
        </h1>
        <p className="mt-1 text-muted-foreground">
          Choose a surveillance mode to begin monitoring
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {actions.map((action) => (
          <Link key={action.to} to={action.to}>
            <Card className="group cursor-pointer border-border/50 transition-all hover:border-primary/50 hover:shadow-lg hover:shadow-primary/5">
              <CardHeader>
                <div className={`mb-2 inline-flex h-10 w-10 items-center justify-center rounded-lg bg-muted ${action.color}`}>
                  <action.icon className="h-5 w-5" />
                </div>
                <CardTitle className="text-lg group-hover:text-primary transition-colors">
                  {action.title}
                </CardTitle>
                <CardDescription>{action.description}</CardDescription>
              </CardHeader>
            </Card>
          </Link>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
  
        <Card className="border-border/50">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Total Detections</p>
            <p className="text-2xl font-bold mt-1">{detectionCount}</p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Live Feed</p>
            <p className="text-2xl font-bold mt-1 text-emerald-400">
              {liveCount}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Uploaded Videos</p>
            <p className="text-2xl font-bold mt-1 text-blue-400">
              {uploadCount}
            </p>
          </CardContent>
        </Card>

        <Card className="border-border/50">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Avg Confidence</p>
            <p className="text-2xl font-bold mt-1 text-amber-400">
              {(avgConfidence * 100).toFixed(1)}%
            </p>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/50">
        <CardHeader>
          <CardTitle>Detection Trend</CardTitle>
          <CardDescription>
            Suspicious activity over time
          </CardDescription>
        </CardHeader>

        <CardContent>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Line
                  type="natural"
                  dataKey="count"
                  stroke="#3b82f6"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/50">
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <CardTitle className="text-base">System Status</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-sm text-muted-foreground">ML Backend</p>
              {backendOnline ? (
                <p className="mt-1 text-sm font-medium text-emerald-400">● Active</p>
              ) : (
                <p className="mt-1 text-sm font-medium text-amber-400">● Awaiting Connection</p>
              )}
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-sm text-muted-foreground">Total Detections</p>
              <p className="mt-1 text-2xl font-bold">{detectionCount}</p>
            </div>
            <div className="rounded-lg bg-muted/50 p-4">
              <p className="text-sm text-muted-foreground">Storage</p>
              <p className="mt-1 text-sm font-medium text-emerald-400">● Active</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
