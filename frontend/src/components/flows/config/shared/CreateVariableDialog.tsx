import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { RESERVED_KEYWORDS, IDENTIFIER_PATTERN } from "@/lib/constants";
import type { VariableType } from "@/lib/types";

const createVariableSchema = (existingVariableNames: string[]) =>
  z
    .object({
      name: z
        .string()
        .min(1, "Variable name is required")
        .max(96, "Variable name must not exceed 96 characters")
        .regex(
          IDENTIFIER_PATTERN,
          "Variable name must start with a letter or underscore and contain only letters, numbers, and underscores"
        )
        .refine((name) => !RESERVED_KEYWORDS.includes(name.toLowerCase()), {
          message: "Variable name is a reserved keyword",
        })
        .refine((name) => !existingVariableNames.includes(name.trim()), {
          message: "A variable with this name already exists",
        }),
      type: z.enum(["string", "number", "boolean", "array"]),
      defaultValue: z.string(),
    })
    .superRefine((data, ctx) => {
      const value = data.defaultValue.trim();
      // Empty or "null" is valid for all types
      if (value === "" || value.toLowerCase() === "null") {
        return;
      }

      // Type-specific validation
      if (data.type === "number") {
        if (!/^-?\d+(\.\d+)?$/.test(value)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Must be a valid number (e.g., 42, -10.5, 0)",
            path: ["defaultValue"],
          });
        }
      } else if (data.type === "boolean") {
        const lower = value.toLowerCase();
        if (!["true", "false"].includes(lower)) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Must be true or false",
            path: ["defaultValue"],
          });
        }
      } else if (data.type === "array") {
        try {
          const parsed = JSON.parse(value);
          if (!Array.isArray(parsed)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              message: 'Must be a valid JSON array (e.g., [], ["item"])',
              path: ["defaultValue"],
            });
          }
        } catch {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            message: "Invalid JSON array format",
            path: ["defaultValue"],
          });
        }
      }
    });

type FormValues = z.infer<ReturnType<typeof createVariableSchema>>;

interface CreateVariableDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: any;
  }) => Promise<void>;
  existingVariableNames: string[];
  defaultType?: "string" | "number" | "boolean" | "array";
}

export function CreateVariableDialog({
  open,
  onOpenChange,
  onCreateVariable,
  existingVariableNames,
  defaultType,
}: CreateVariableDialogProps) {
  const [isLoading, setIsLoading] = useState(false);

  const form = useForm<FormValues>({
    resolver: zodResolver(createVariableSchema(existingVariableNames)),
    defaultValues: {
      name: "",
      type: (defaultType || "string") as "string" | "number" | "boolean" | "array",
      defaultValue: "",
    },
  });

  const selectedType = form.watch("type");

  // Get type-specific placeholder
  const getPlaceholder = (varType: string): string => {
    switch (varType) {
      case "string":
        return "Enter any text value or leave empty";
      case "number":
        return "e.g., 42, -10.5, 0";
      case "boolean":
        return "true or false";
      case "array":
        return '[] or ["item1", "item2"]';
      default:
        return "Enter default value";
    }
  };

  // Get type-specific help text
  const getHelpText = (varType: string): string => {
    switch (varType) {
      case "string":
        return "Enter any text value or leave empty";
      case "number":
        return "Enter a number (e.g., 42, -10.5)";
      case "boolean":
        return "Enter 'true' or 'false'";
      case "array":
        return 'Enter JSON array (e.g., [], ["item1", "item2"])';
      default:
        return "";
    }
  };

  // Process default value for submission
  const processDefaultValue = (varType: string, value: string): any => {
    // Empty string or "null" becomes null
    if (value.trim() === "" || value.toLowerCase() === "null") {
      return null;
    }

    if (varType === "string") {
      return value;
    }

    if (varType === "number") {
      return parseFloat(value.trim());
    }

    if (varType === "boolean") {
      return value.toLowerCase().trim() === "true";
    }

    if (varType === "array") {
      return JSON.parse(value);
    }

    return value;
  };

  // Handle form submission
  const onSubmit = async (values: FormValues) => {
    setIsLoading(true);

    try {
      await onCreateVariable({
        name: values.name.trim(),
        type: values.type.toUpperCase() as VariableType, // Convert to uppercase for backend (STRING, NUMBER, BOOLEAN, ARRAY)
        default: processDefaultValue(values.type, values.defaultValue),
      });

      // Success - close dialog and reset form
      form.reset();
      onOpenChange(false);
    } catch (error) {
      // Error handling is done by parent component
      console.error("Error creating variable:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>Create New Variable</DialogTitle>
          <DialogDescription>
            Define a new flow variable with a name, type, and optional default
            value.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Variable Name */}
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Variable Name</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="Enter variable name"
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>
                    Must be 1-96 characters and unique
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Variable Type */}
            <FormField
              control={form.control}
              name="type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Type</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    value={field.value}
                    disabled={isLoading || !!defaultType}
                  >
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="string">String</SelectItem>
                      <SelectItem value="number">Number</SelectItem>
                      <SelectItem value="boolean">Boolean</SelectItem>
                      <SelectItem value="array">Array</SelectItem>
                    </SelectContent>
                  </Select>
                  {defaultType && (
                    <FormDescription>
                      Type is pre-selected based on field requirements
                    </FormDescription>
                  )}
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Default Value */}
            <FormField
              control={form.control}
              name="defaultValue"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Default Value (Optional)</FormLabel>
                  <FormControl>
                    <Input
                      placeholder={getPlaceholder(selectedType)}
                      {...field}
                      disabled={isLoading}
                    />
                  </FormControl>
                  <FormDescription>
                    {getHelpText(selectedType)}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={isLoading}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading && <LoadingSpinner size="sm" variant="light" className="mr-2" />}
                Create Variable
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
