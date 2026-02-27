import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { X, Plus } from "lucide-react";
import { useCreateFlowMutation } from "@/hooks/queries/useFlowsQuery";
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
import { Badge } from "@/components/ui/badge";
import { CharacterCounter } from "@/components/flows/config/shared/CharacterCounter";
import { FieldHelp } from "@/components/flows/config/shared/FieldHelp";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

const createFlowSchema = (
  existingFlowNames: string[],
  existingTriggerKeywords: Map<string, string>
) =>
  z.object({
    name: z
      .string()
      .min(1, "Flow name is required")
      .max(96, "Flow name must not exceed 96 characters")
      .refine((name) => !existingFlowNames.includes(name.trim()), {
        message: "A flow with this name already exists",
      }),
    triggerKeywords: z
      .array(z.string())
      .min(1, "At least one trigger keyword is required")
      .refine(
        (keywords) => {
          // Check if any keyword conflicts with existing keywords
          for (const keyword of keywords) {
            const keywordUpper = keyword.toUpperCase();
            if (existingTriggerKeywords.has(keywordUpper)) {
              return false;
            }
          }
          return true;
        },
        {
          message: "One or more keywords are already in use by another flow",
        }
      ),
  });

type FormValues = z.infer<ReturnType<typeof createFlowSchema>>;

interface CreateFlowDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateFlow?: (name: string, triggerKeywords: string[]) => void;
  onSuccess?: (newFlow: any) => void | Promise<void>;
  existingFlowNames?: string[];
  existingTriggerKeywords?: Map<string, string>; // Map of keyword -> flow name
  botId: string;
}

export default function CreateFlowDialog({
  open,
  onOpenChange,
  onCreateFlow,
  onSuccess,
  existingFlowNames = [],
  existingTriggerKeywords = new Map(),
  botId,
}: CreateFlowDialogProps) {
  const createFlowMutation = useCreateFlowMutation(botId);
  const [newKeyword, setNewKeyword] = useState("");
  const [keywordError, setKeywordError] = useState<string | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(
      createFlowSchema(existingFlowNames, existingTriggerKeywords)
    ),
    defaultValues: {
      name: "",
      triggerKeywords: [],
    },
  });

  const onSubmit = async (values: FormValues) => {
    // Create initial node: a single text node (terminal - no routes)
    const messageNodeId = "message_start";

    const initialNodes = {
      [messageNodeId]: {
        id: messageNodeId,
        type: "TEXT" as const,
        name: "Welcome Message",
        config: {
          type: "TEXT" as const,
          text: "Welcome! This is your new flow.",
        },
        routes: [], // No routes = terminal node
        position: { x: 100, y: 200 },
      },
    };

    // Use React Query mutation to create the flow
    createFlowMutation.mutate(
      {
        name: values.name.trim(),
        trigger_keywords: values.triggerKeywords,
        start_node_id: messageNodeId,
        nodes: initialNodes,
      },
      {
        onSuccess: (newFlow) => {
          // Call legacy callback if provided
          if (onCreateFlow) {
            onCreateFlow(values.name.trim(), values.triggerKeywords);
          }
          // Call onSuccess callback with the new flow
          if (onSuccess) {
            onSuccess(newFlow);
          }
          form.reset();
          setNewKeyword("");
          setKeywordError(null);
          onOpenChange(false);
        },
      }
    );
  };

  // Add trigger keyword
  const handleAddKeyword = () => {
    const keyword = newKeyword.trim();
    const currentKeywords = form.getValues("triggerKeywords");

    if (!keyword) {
      setKeywordError("Keyword cannot be empty");
      return;
    }

    // Check if keyword is wildcard "*"
    const isWildcard = keyword === "*";

    // Validate character set (only if not wildcard)
    if (!isWildcard && !/^[A-Za-z0-9 _-]+$/.test(keyword)) {
      setKeywordError(
        "Keyword can only contain letters, numbers, spaces, underscores, and hyphens. No punctuation or special characters allowed."
      );
      return;
    }

    // Check for duplicates within this flow (case-insensitive)
    if (
      currentKeywords.some((k) => k.toLowerCase() === keyword.toLowerCase())
    ) {
      setKeywordError("Keyword already exists in this flow");
      return;
    }

    // Check if keyword is already used by another flow (case-insensitive)
    const keywordUpper = keyword.toUpperCase();
    if (existingTriggerKeywords.has(keywordUpper)) {
      const flowName = existingTriggerKeywords.get(keywordUpper);
      setKeywordError(`Keyword already used by flow "${flowName}"`);
      return;
    }

    // Handle wildcard logic
    if (isWildcard) {
      // If adding wildcard and other keywords exist, replace all with wildcard
      form.setValue("triggerKeywords", ["*"], { shouldValidate: true });
    } else {
      // If adding regular keyword and wildcard exists, replace wildcard
      if (currentKeywords.includes("*")) {
        form.setValue("triggerKeywords", [keyword], { shouldValidate: true });
      } else {
        form.setValue("triggerKeywords", [...currentKeywords, keyword], {
          shouldValidate: true,
        });
      }
    }

    setNewKeyword("");
    setKeywordError(null);
  };

  // Remove trigger keyword
  const handleRemoveKeyword = (keyword: string) => {
    const currentKeywords = form.getValues("triggerKeywords");
    const newKeywords = currentKeywords.filter((k) => k !== keyword);
    form.setValue("triggerKeywords", newKeywords, { shouldValidate: true });
  };

  // Handle keyword input key press
  const handleKeywordKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddKeyword();
    }
  };

  const triggerKeywords = form.watch("triggerKeywords");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Flow</DialogTitle>
          <DialogDescription>
            Enter a unique name for your flow and trigger keywords
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
                    <FormLabel>Flow Name</FormLabel>
                    <CharacterCounter
                      current={field.value?.length || 0}
                      max={SystemConstraints.MAX_FLOW_NAME_LENGTH}
                    />
                  </div>
                  <FormControl>
                    <Input
                      placeholder="Enter flow name (e.g., 'Customer Support Flow')"
                      {...field}
                      disabled={createFlowMutation.isPending}
                      maxLength={SystemConstraints.MAX_FLOW_NAME_LENGTH}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="triggerKeywords"
              render={() => (
                <FormItem>
                  <FormLabel>Trigger Keywords</FormLabel>

                  {/* Input and Add Button */}
                  <div className="space-y-2">
                    <div className="flex gap-2">
                      <Input
                        placeholder="Enter keyword (e.g., START, HELP)"
                        value={newKeyword}
                        onChange={(e) => {
                          setNewKeyword(e.target.value);
                          setKeywordError(null);
                        }}
                        onKeyDown={handleKeywordKeyDown}
                        maxLength={SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH}
                        disabled={createFlowMutation.isPending}
                        className={cn(
                          keywordError && "border-destructive focus-visible:ring-destructive"
                        )}
                      />
                      <Button
                        type="button"
                        onClick={handleAddKeyword}
                        size="sm"
                        className="shrink-0"
                        disabled={createFlowMutation.isPending}
                      >
                        <Plus className="h-4 w-4 mr-1" />
                        Add
                      </Button>
                    </div>
                    {keywordError && (
                      <p className="text-sm text-destructive">{keywordError}</p>
                    )}
                  </div>

                  {/* Keywords Display */}
                  <div className="space-y-1">
                    {triggerKeywords.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5">
                        {triggerKeywords.map((keyword) => (
                          <Badge
                            key={keyword}
                            variant="secondary"
                            className="flex items-center gap-1 pl-2 pr-1"
                          >
                            {keyword === "*" ? "* (accepts any message)" : keyword}
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => handleRemoveKeyword(keyword)}
                              className="ml-1 h-5 w-5 hover:bg-muted"
                              disabled={createFlowMutation.isPending}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-destructive">
                        No keywords added. At least one trigger keyword is required.
                      </p>
                    )}
                    <FieldHelp
                      text="Words that start this flow when a user sends them"
                      tooltip={
                        <>
                          <p className="mb-2">
                            When a user sends a message matching any of these keywords, this flow will start. Matching ignores capitalization (START = start = Start).
                          </p>
                          <p className="text-xs font-medium mt-2">Examples:</p>
                          <p className="mt-1 text-xs">
                            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                              START
                            </code>
                            ,{" "}
                            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                              HELP
                            </code>
                            ,{" "}
                            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                              SUPPORT
                            </code>
                          </p>
                          <p className="text-xs font-medium mt-2">Catch-all option:</p>
                          <p className="mt-1 text-xs">
                            Use{" "}
                            <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                              *
                            </code>{" "}
                            to start this flow for any message. Note: this should be the only keyword when used.
                          </p>
                        </>
                      }
                    />
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={createFlowMutation.isPending}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={createFlowMutation.isPending}>
                {createFlowMutation.isPending && (
                  <LoadingSpinner size="sm" variant="light" className="mr-2" />
                )}
                Create Flow
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
