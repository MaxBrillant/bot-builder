import { User, ChevronDown, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { MyAccountDialog } from "./MyAccountDialog";
import { useAuth } from "@/contexts/AuthContext";
import { useNavigate } from "react-router-dom";

interface UserDropdownProps {
  size?: "sm" | "lg" | "default" | "icon";
  onBeforeLogout?: () => Promise<boolean>;
}

export function UserDropdown({ size = "sm", onBeforeLogout }: UserDropdownProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    // Check if there's a pre-logout hook (e.g., unsaved changes check)
    if (onBeforeLogout) {
      const shouldProceed = await onBeforeLogout();
      if (!shouldProceed) {
        return; // User cancelled logout
      }
    }

    await logout();
    navigate("/login");
  };

  if (!user) return null;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size={size}
          className="flex items-center gap-2"
        >
          <User className="w-4 h-4" />
          <span className="hidden sm:inline">{user.email}</span>
          <ChevronDown className="w-3 h-3" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <MyAccountDialog />
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={handleLogout}>
          <LogOut className="mr-2 h-4 w-4" />
          Logout
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
