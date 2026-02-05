import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useCreateBotMutation } from "@/hooks/queries/useBotsQuery";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { Textarea } from "@/components/ui/textarea";
import { CharacterCounter } from "@/components/flows/config/shared/CharacterCounter";
import { SystemConstraints } from "@/lib/types";

const formSchema = z.object({
  name: z
    .string()
    .min(3, "Name must be at least 3 characters")
    .max(96, "Name must not exceed 96 characters"),
  description: z
    .string()
    .max(512, "Description must not exceed 512 characters")
    .optional(),
});

type FormValues = z.infer<typeof formSchema>;

interface CreateBotDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export default function CreateBotDialog({
  open,
  onOpenChange,
  onSuccess,
}: CreateBotDialogProps) {
  const createBotMutation = useCreateBotMutation();

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      description: "",
    },
  });

  const onSubmit = async (values: FormValues) => {
    createBotMutation.mutate(
      {
        name: values.name,
        description: values.description || undefined,
      },
      {
        onSuccess: () => {
          form.reset();
          onOpenChange(false);
          onSuccess();
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Bot</DialogTitle>
          <DialogDescription>
            Create a new bot to start building your conversational flows.
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
                      disabled={createBotMutation.isPending}
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
                      disabled={createBotMutation.isPending}
                      maxLength={SystemConstraints.MAX_BOT_DESCRIPTION_LENGTH}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={createBotMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createBotMutation.isPending}>
                {createBotMutation.isPending && <LoadingSpinner size="sm" variant="light" className="mr-2" />}
                Create Bot
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
