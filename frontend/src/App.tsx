import {
  createBrowserRouter,
  RouterProvider,
  Outlet,
  Navigate,
} from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "./lib/queryClient";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Toaster } from "@/components/ui/sonner";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import BotsPage from "./pages/BotsPage";
import FlowEditorPage from "./pages/FlowEditorPage";
import OAuthCallbackPage from "./pages/OAuthCallbackPage";

// Protected Route Component
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Public Route Component (redirects to /bots if already authenticated)
function PublicRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <LoadingSpinner size="lg" className="mx-auto" />
          <p className="mt-4 text-muted-foreground">Loading...</p>
        </div>
      </div>
    );
  }

  if (user) {
    // Check if there's a redirect parameter in the URL
    const searchParams = new URLSearchParams(window.location.search);
    const redirect = searchParams.get("redirect");
    const destination = redirect ? decodeURIComponent(redirect) : "/bots";
    return <Navigate to={destination} replace />;
  }

  return <>{children}</>;
}

// Layout route: provides auth context and toast notifications to all routes
function AppLayout() {
  return (
    <AuthProvider>
      <Toaster />
      <Outlet />
    </AuthProvider>
  );
}

const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      // Public routes - redirect to /bots if already logged in
      { path: "/", element: <PublicRoute><LoginPage /></PublicRoute> },
      { path: "/login", element: <PublicRoute><LoginPage /></PublicRoute> },
      { path: "/register", element: <PublicRoute><RegisterPage /></PublicRoute> },
      // OAuth callback route - handles authentication
      { path: "/auth/callback", element: <OAuthCallbackPage /> },
      // Protected routes - require authentication
      { path: "/bots", element: <ProtectedRoute><BotsPage /></ProtectedRoute> },
      { path: "/bots/:botId/flows/:flowId", element: <ProtectedRoute><FlowEditorPage /></ProtectedRoute> },
      { path: "/bots/:botId", element: <ProtectedRoute><FlowEditorPage /></ProtectedRoute> },
    ],
  },
]);

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
          <ReactQueryDevtools initialIsOpen={false} />
        </QueryClientProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
