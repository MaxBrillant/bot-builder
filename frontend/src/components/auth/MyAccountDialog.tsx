import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { deleteUserData } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { toast } from "sonner";

const deleteAccountSchema = (expectedEmail: string) =>
  z.object({
    email: z
      .string()
      .email("Invalid email address")
      .refine((val) => val === expectedEmail, {
        message: "Email does not match",
      }),
  });

type FormValues = z.infer<ReturnType<typeof deleteAccountSchema>>;

export function MyAccountDialog() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isDeleting, setIsDeleting] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  const form = useForm<FormValues>({
    resolver: user?.email
      ? zodResolver(deleteAccountSchema(user.email))
      : undefined,
    defaultValues: {
      email: "",
    },
  });

  const onSubmit = async (_values: FormValues) => {
    try {
      setIsDeleting(true);
      await deleteUserData();

      setDeleteDialogOpen(false);
      setIsOpen(false);
      form.reset();

      // Navigate to login FIRST to prevent 401 interceptor from capturing current path
      navigate("/login", { replace: true });

      // Then logout (which will clear state but won't redirect since we're already on /login)
      setTimeout(async () => {
        await logout();
        toast.success("All your data has been deleted");
      }, 100);
    } catch (error) {
      toast.error("Failed to delete data");
      console.error(error);
    } finally {
      setIsDeleting(false);
    }
  };

  // Reset form when dialog opens/closes
  const handleDeleteDialogChange = (open: boolean) => {
    setDeleteDialogOpen(open);
    if (!open) {
      form.reset();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <button className="w-full text-left px-2 py-1.5 text-sm hover:bg-accent rounded-sm">
          My Account
        </button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>My Account</DialogTitle>
        </DialogHeader>

        <div className="space-y-6 py-4">
          {/* User Info */}
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Email
              </label>
              <p className="text-base">{user?.email}</p>
            </div>
            <div>
              <label className="text-sm font-medium text-muted-foreground">
                Member Since
              </label>
              <p className="text-sm">
                {new Date(user?.created_at || "").toLocaleDateString()}
              </p>
            </div>
            {user?.oauth_provider && (
              <div>
                <label className="text-sm font-medium text-muted-foreground">
                  Connected via
                </label>
                <p className="text-sm capitalize">{user.oauth_provider}</p>
              </div>
            )}
          </div>

          {/* Danger Zone */}
          <div className="border-t pt-4">
            <h3 className="text-sm font-semibold text-destructive mb-1">
              Danger Zone
            </h3>
            <p className="text-xs text-muted-foreground mb-3">
              Delete all your data permanently. This action cannot be undone.
            </p>

            <AlertDialog open={deleteDialogOpen} onOpenChange={handleDeleteDialogChange}>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" size="sm" disabled={isDeleting}>
                  Delete My Data
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete all your data?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will permanently delete your account, all bots, flows,
                    and sessions. This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>

                <Form {...form}>
                  <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                    <FormField
                      control={form.control}
                      name="email"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel className="text-sm font-medium">
                            Type your email address to confirm:{" "}
                            <span className="font-semibold">{user?.email}</span>
                          </FormLabel>
                          <FormControl>
                            <Input
                              type="email"
                              {...field}
                              placeholder="Enter your email address"
                              disabled={isDeleting}
                              autoComplete="off"
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <AlertDialogFooter>
                      <AlertDialogCancel disabled={isDeleting}>
                        Cancel
                      </AlertDialogCancel>
                      <Button
                        type="submit"
                        variant="destructive"
                        disabled={isDeleting}
                      >
                        {isDeleting && (
                          <LoadingSpinner size="sm" variant="light" className="mr-2" />
                        )}
                        Delete everything
                      </Button>
                    </AlertDialogFooter>
                  </form>
                </Form>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
