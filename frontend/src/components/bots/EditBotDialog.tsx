import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Copy, RotateCw, MessageCircle } from "lucide-react";
import { toast } from "sonner";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  useUpdateBotMutation,
  useRegenerateWebhookSecretMutation,
} from "@/hooks/queries/useBotsQuery";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { CharacterCounter } from "@/components/flows/config/shared/CharacterCounter";
import { SystemConstraints } from "@/lib/types";
import WhatsAppStatusBadge from "./WhatsAppStatusBadge";
import WhatsAppConnectionModal from "./WhatsAppConnectionModal";
import { Separator } from "@/components/ui/separator";

const formSchema = z.object({
  name: z
    .string()
    .min(3, "Name must be at least 3 characters")
    .max(96, "Name must not exceed 96 characters"),
  description: z
    .string()
    .max(512, "Description must not exceed 512 characters")
    .optional(),
  status: z.enum(["ACTIVE", "INACTIVE"]),
});

type FormValues = z.infer<typeof formSchema>;

interface EditBotDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  bot: {
    bot_id: string;
    name: string;
    description?: string;
    status: string;
    webhook_secret?: string;
    whatsapp_status?: "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";
    whatsapp_phone_number?: string;
  } | null;
  onSuccess: (updatedBot?: any) => void;
}

export default function EditBotDialog({
  open,
  onOpenChange,
  bot,
  onSuccess,
}: EditBotDialogProps) {
  // React Query mutations
  const updateBotMutation = useUpdateBotMutation();
  const regenerateSecretMutation = useRegenerateWebhookSecretMutation();

  const [webhookSecret, setWebhookSecret] = useState<string>("");
  const [showRegenerateDialog, setShowRegenerateDialog] = useState(false);
  const [whatsappDialogOpen, setWhatsappDialogOpen] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
      status: "ACTIVE",
    },
  });

  // Update form and webhook secret when bot changes
  useEffect(() => {
    if (bot) {
      form.reset({
        name: bot.name,
        description: bot.description || "",
        status: bot.status as "ACTIVE" | "INACTIVE",
      });
      setWebhookSecret(bot.webhook_secret || "");
    }
  }, [bot, form]);

  const onSubmit = async (values: FormValues) => {
    if (!bot) return;

    updateBotMutation.mutate(
      {
        botId: bot.bot_id,
        data: {
          name: values.name,
          description: values.description || undefined,
          status: values.status,
        },
      },
      {
        onSuccess: () => {
          onOpenChange(false);
          onSuccess();
        },
      }
    );
  };

  const handleCopySecret = async () => {
    try {
      await navigator.clipboard.writeText(webhookSecret);
      toast.success("Webhook secret copied!");
    } catch (error) {
      toast.error("Failed to copy webhook secret");
    }
  };

  const handleRegenerateSecret = async () => {
    if (!bot) return;

    regenerateSecretMutation.mutate(bot.bot_id, {
      onSuccess: (response) => {
        const newSecret = response.data.webhook_secret;
        setWebhookSecret(newSecret);
        setShowRegenerateDialog(false);
      },
    });
  };

  if (!bot) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Edit Bot</DialogTitle>
          <DialogDescription>
            Update your bot's information and settings.
          </DialogDescription>
        </DialogHeader>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel>Name</FormLabel>
                    <CharacterCounter
                      current={field.value?.length || 0}
                      max={SystemConstraints.MAX_BOT_NAME_LENGTH}
                    />
                  </div>
                  <FormControl>
                    <Input
                      placeholder="My Awesome Bot"
                      {...field}
                      disabled={updateBotMutation.isPending}
                      maxLength={SystemConstraints.MAX_BOT_NAME_LENGTH}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <div className="flex items-center justify-between">
                    <FormLabel>Description (Optional)</FormLabel>
                    <CharacterCounter
                      current={field.value?.length || 0}
                      max={SystemConstraints.MAX_BOT_DESCRIPTION_LENGTH}
                    />
                  </div>
                  <FormControl>
                    <Textarea
                      placeholder="Describe what this bot does..."
                      className="resize-none"
                      rows={4}
                      {...field}
                      disabled={updateBotMutation.isPending}
                      maxLength={SystemConstraints.MAX_BOT_DESCRIPTION_LENGTH}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="status"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Status</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                    disabled={updateBotMutation.isPending}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue placeholder="Select status" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="ACTIVE">Active</SelectItem>
                      <SelectItem value="INACTIVE">Inactive</SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Webhook Secret Section */}
            <div className="space-y-2">
              <Label>Webhook Secret</Label>
              <div className="flex gap-2">
                <Input
                  value={webhookSecret}
                  readOnly
                  className="flex-1 font-mono text-sm"
                  placeholder="No webhook secret available"
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleCopySecret}
                  disabled={!webhookSecret || updateBotMutation.isPending}
                  title="Copy webhook secret"
                >
                  <Copy className="h-4 w-4" />
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={() => setShowRegenerateDialog(true)}
                  disabled={updateBotMutation.isPending}
                  title="Regenerate webhook secret"
                >
                  <RotateCw className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* WhatsApp Connection Section */}
            <Separator />
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <Label className="text-base">WhatsApp Connection</Label>
                  <p className="text-sm text-muted-foreground mt-1">
                    Connect your bot to WhatsApp using Evolution API
                  </p>
                </div>
                <WhatsAppStatusBadge
                  status={bot?.whatsapp_status}
                  phoneNumber={bot?.whatsapp_phone_number}
                />
              </div>
              <Button
                type="button"
                variant="outline"
                onClick={() => setWhatsappDialogOpen(true)}
                className="w-full"
              >
                <MessageCircle className="h-4 w-4 mr-2" />
                {bot?.whatsapp_status === "CONNECTED"
                  ? "Manage WhatsApp Connection"
                  : "Connect to WhatsApp"}
              </Button>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={updateBotMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={updateBotMutation.isPending}>
                {updateBotMutation.isPending && <LoadingSpinner size="sm" variant="light" className="mr-2" />}
                Save Changes
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>

      {/* Regenerate Confirmation Dialog */}
      <AlertDialog
        open={showRegenerateDialog}
        onOpenChange={setShowRegenerateDialog}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Regenerate Webhook Secret?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to regenerate the webhook secret? This will
              invalidate the old secret.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={regenerateSecretMutation.isPending}>
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRegenerateSecret}
              disabled={regenerateSecretMutation.isPending}
            >
              {regenerateSecretMutation.isPending && (
                <LoadingSpinner size="sm" variant="light" className="mr-2" />
              )}
              Regenerate
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* WhatsApp Connection Modal */}
      {bot && (
        <WhatsAppConnectionModal
          botId={bot.bot_id}
          botName={bot.name}
          open={whatsappDialogOpen}
          onOpenChange={setWhatsappDialogOpen}
          onConnected={() => {
            // Refresh bot data after connection
            onSuccess();
          }}
        />
      )}
    </Dialog>
  );
}
