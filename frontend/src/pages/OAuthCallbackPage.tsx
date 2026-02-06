import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

/**
 * OAuth Callback Page
 *
 * Handles the redirect from OAuth provider (Google).
 * SECURITY: Token is NOT in URL - it's in an httpOnly cookie set by the backend.
 * This page just verifies the cookie is valid by calling /auth/me.
 */
export default function OAuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { verifyAuthCookie } = useAuth();

  useEffect(() => {
    const error = searchParams.get("error");
    const redirect = searchParams.get("redirect");

    if (error) {
      // Handle OAuth error - map error codes to user-friendly messages
      console.error("OAuth error:", error);
      navigate(`/login?error=${error}`);
      return;
    }

    // SECURITY: Token is in httpOnly cookie, not URL
    // Verify the cookie is valid by calling /auth/me
    verifyAuthCookie()
      .then(() => {
        // Navigate to redirect URL if present, otherwise go to /bots
        // Validate redirect is a relative path to prevent open redirect
        let targetPath = "/bots";
        if (redirect) {
          const decodedRedirect = decodeURIComponent(redirect);
          // Only allow relative paths starting with /
          if (decodedRedirect.startsWith("/") && !decodedRedirect.startsWith("//")) {
            targetPath = decodedRedirect;
          }
        }
        navigate(targetPath);
      })
      .catch((error) => {
        console.error("Failed to verify authentication:", error);
        navigate("/login?error=auth_failed");
      });
  }, [searchParams, navigate, verifyAuthCookie]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-muted/30">
      <div className="text-center">
        <LoadingSpinner size="lg" className="mx-auto" />
        <p className="mt-4 text-muted-foreground">Completing sign in...</p>
      </div>
    </div>
  );
}
