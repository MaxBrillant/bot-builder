import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { AlertTriangle } from "lucide-react";
import { useDeleteBotMutation } from "@/hooks/queries/useBotsQuery";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { IconBadge } from "@/components/ui/icon-badge";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const deleteBotSchema = (expectedName: string) =>
  z.object({
    confirmName: z
      .string()
      .refine((val) => val === expectedName, {
        message: `Must match bot name: "${expectedName}"`,
      }),
  });

type FormValues = z.infer<ReturnType<typeof deleteBotSchema>>;

interface DeleteBotDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  bot: {
    bot_id: string;
    name: string;
  } | null;
  onSuccess: () => void;
}

export default function DeleteBotDialog({
  open,
  onOpenChange,
  bot,
  onSuccess,
}: DeleteBotDialogProps) {
  const deleteBotMutation = useDeleteBotMutation();

  const form = useForm<FormValues>({
    resolver: bot ? zodResolver(deleteBotSchema(bot.name)) : undefined,
    defaultValues: {
      confirmName: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    if (!bot) return;

    deleteBotMutation.mutate(bot.bot_id, {
      onSuccess: () => {
        form.reset();
        onOpenChange(false);
        onSuccess();
      },
    });
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      form.reset();
    }
    onOpenChange(newOpen);
  };

  if (!bot) return null;

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <div className="flex items-center gap-2">
            <IconBadge icon={AlertTriangle} variant="red" />
            <AlertDialogTitle>Delete Bot</AlertDialogTitle>
          </div>
          <AlertDialogDescription className="pt-2">
            <p>
              Are you sure you want to delete <strong>"{bot.name}"</strong>?
              This action cannot be undone. All flows and conversations
              associated with this bot will be permanently deleted.
            </p>
          </AlertDialogDescription>
        </AlertDialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="confirmName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel className="text-sm font-medium text-foreground">
                    To confirm, type the bot name below:
                  </FormLabel>
                  <FormControl>
                    <Input
                      {...field}
                      placeholder={bot.name}
                      disabled={deleteBotMutation.isPending}
                      className="font-mono"
                      autoComplete="off"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <AlertDialogFooter>
              <AlertDialogCancel disabled={deleteBotMutation.isPending}>
                Cancel
              </AlertDialogCancel>
              <Button
                type="submit"
                variant="destructive"
                disabled={deleteBotMutation.isPending}
              >
                {deleteBotMutation.isPending && (
                  <LoadingSpinner size="sm" variant="light" className="mr-2" />
                )}
                Delete Bot
              </Button>
            </AlertDialogFooter>
          </form>
        </Form>
      </AlertDialogContent>
    </AlertDialog>
  );
}
