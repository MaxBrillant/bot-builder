import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";

interface NotFoundProps {
  title?: string;
  message?: string;
  showBackButton?: boolean;
}

export function NotFound({
  title = "Page Not Found",
  message = "The page you're looking for doesn't exist or has been deleted.",
  showBackButton = true,
}: NotFoundProps) {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-muted/30 px-4">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-destructive/10 rounded-full mb-6">
          <AlertCircle className="w-10 h-10 text-destructive" />
        </div>

        <h1 className="text-6xl font-bold tracking-tighter mb-2">404</h1>
        <h2 className="text-2xl font-semibold tracking-tight mb-4">{title}</h2>
        <p className="text-base text-muted-foreground leading-relaxed mb-8">{message}</p>

        {showBackButton && (
          <div className="flex gap-3 justify-center">
            <Button variant="outline" onClick={() => navigate(-1)}>
              Go Back
            </Button>
            <Button onClick={() => navigate("/bots")}>
              Go to My Bots
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
