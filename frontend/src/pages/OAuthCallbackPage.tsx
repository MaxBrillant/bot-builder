import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

export default function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { setAuthFromToken } = useAuth();

  useEffect(() => {
    const token = searchParams.get("token");
    const error = searchParams.get("error");
    const redirect = searchParams.get("redirect");

    if (error) {
      // Handle OAuth error
      console.error("OAuth error:", error);
      navigate("/login?error=oauth_failed");
      return;
    }

    if (token) {
      // Store token and fetch user data
      setAuthFromToken(token)
        .then(() => {
          // Navigate to redirect URL if present, otherwise go to /bots
          const decodedRedirect = redirect ? decodeURIComponent(redirect) : null;
          navigate(decodedRedirect || "/bots");
        })
        .catch((error) => {
          console.error("Failed to authenticate:", error);
          navigate("/login?error=auth_failed");
        });
    } else {
      // No token or error - redirect to login
      navigate("/login?error=oauth_failed");
    }
  }, [searchParams, navigate, setAuthFromToken]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30">
      <div className="text-center">
        <LoadingSpinner size="lg" className="mx-auto" />
        <p className="mt-4 text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}
