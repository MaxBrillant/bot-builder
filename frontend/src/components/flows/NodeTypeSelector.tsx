import { useState, useEffect } from "react";
import {
  MessageSquare,
  List,
  Globe,
  GitBranch,
  MessageCircle,
} from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { ConditionSelector } from "./config/shared/ConditionSelector";
import { getDefaultCondition } from "@/lib/routeConditionUtils";
import type { NodeType, FlowNode } from "@/lib/types";

interface NodeTypeOption {
  type: NodeType;
  label: string;
  icon: React.ElementType;
  description: string;
  color: string;
}

const nodeTypeOptions: NodeTypeOption[] = [
  {
    type: "PROMPT",
    label: "Prompt",
    icon: MessageSquare,
    description: "Collect user input",
    color: "text-node-prompt hover:bg-accent",
  },
  {
    type: "MENU",
    label: "Menu",
    icon: List,
    description: "Present options",
    color: "text-node-menu hover:bg-accent",
  },
  {
    type: "API_ACTION",
    label: "API Action",
    icon: Globe,
    description: "Call external API",
    color: "text-node-api hover:bg-accent",
  },
  {
    type: "LOGIC_EXPRESSION",
    label: "Logic",
    icon: GitBranch,
    description: "Conditional routing",
    color: "text-node-logic hover:bg-accent",
  },
  {
    type: "MESSAGE",
    label: "Message",
    icon: MessageCircle,
    description: "Display message",
    color: "text-node-message hover:bg-accent",
  },
];

interface NodeTypeSelectorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectType?: (type: NodeType, condition?: string) => void;
  onSelect?: (type: any, condition: any) => void;
  onUpdateCondition?: (newCondition: string) => void; // Update existing route condition (implicit save on close)
  children?: React.ReactNode;
  parentNode?: FlowNode | null;
  preSelectedType?: NodeType;
  preFilledCondition?: string; // Pre-filled condition from edge click
  availableVariables?: string[]; // Available variables for autocomplete
}

export default function NodeTypeSelector({
  open,
  onOpenChange,
  onSelectType,
  onSelect,
  onUpdateCondition,
  children,
  parentNode,
  preSelectedType,
  preFilledCondition,
  availableVariables = [],
}: NodeTypeSelectorProps) {
  const [condition, setCondition] = useState("");
  const [error, setError] = useState("");
  const [selectedType, setSelectedType] = useState<NodeType | undefined>(preSelectedType);

  // Check if we need to show condition input
  // Show for all branching node types (MENU, API_ACTION, LOGIC_EXPRESSION)
  const needsCondition =
    parentNode &&
    ["MENU", "API_ACTION", "LOGIC_EXPRESSION"].includes(parentNode.type);

  // Update selected type when preSelectedType changes
  useEffect(() => {
    setSelectedType(preSelectedType);
  }, [preSelectedType]);

  // Initialize condition: use pre-filled value from edge, or smart default
  useEffect(() => {
    if (needsCondition && parentNode) {
      if (preFilledCondition !== undefined) {
        setCondition(preFilledCondition);
      } else {
        const defaultCond = getDefaultCondition(
          parentNode,
          parentNode.routes || []
        );
        setCondition(defaultCond);
      }
    }
  }, [needsCondition, parentNode, preFilledCondition]);

  const handleSelectType = (type: NodeType) => {
    // Validate condition if needed
    if (needsCondition) {
      const trimmedCondition = condition.trim();
      if (!trimmedCondition) {
        setError("Condition is required");
        return;
      }

      // Note: We DO allow duplicate conditions now!
      // If a condition already exists, the system will use route overtaking
      // to insert the new node INTO that existing route instead of creating a new branch

      if (onSelectType) {
        onSelectType(type, trimmedCondition);
      } else if (onSelect) {
        onSelect(type, trimmedCondition);
      }
    } else {
      if (onSelectType) {
        onSelectType(type);
      } else if (onSelect) {
        onSelect(type, undefined);
      }
    }

    // Reset state and close
    setCondition("");
    setError("");
    onOpenChange(false);
  };

  const handleConditionKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      const typeToInsert = selectedType || preSelectedType;
      if (typeToInsert) {
        handleSelectType(typeToInsert);
      }
    }
  };

  // Reset state when dialog closes
  // Implicit save: if condition changed and we have an update handler, save it
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Check if condition was modified from original
      const trimmedCondition = condition.trim();
      const originalCondition = preFilledCondition?.trim() || "";
      const conditionChanged = trimmedCondition && trimmedCondition !== originalCondition;

      // Implicit save on close if condition changed
      if (conditionChanged && onUpdateCondition) {
        onUpdateCondition(trimmedCondition);
      }

      setCondition("");
      setError("");
      setSelectedType(undefined);
    }
    onOpenChange(newOpen);
  };


  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent className="w-80 p-2 bg-background" align="start">
        <div className="space-y-2">
          <div className="px-2 py-2 text-xs font-semibold text-muted-foreground uppercase">
            Select Node Type
          </div>

          {/* Condition Selector - only show for branching nodes */}
          {needsCondition && parentNode && (
            <div className="px-2 pb-2 border-b border-border">
              <ConditionSelector
                nodeType={parentNode.type}
                nodeConfig={parentNode.config}
                value={condition}
                onChange={(value) => {
                  setCondition(value);
                  setError("");
                }}
                onKeyDown={handleConditionKeyDown}
                error={error}
                placeholder={
                  parentNode.type === "MENU"
                    ? "Select menu option"
                    : parentNode.type === "API_ACTION"
                    ? "Select condition"
                    : "e.g. context.age > 18"
                }
                availableVariables={availableVariables}
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-2">
            {nodeTypeOptions.map((option) => {
              const Icon = option.icon;
              const isSelected = selectedType === option.type;
              return (
                <Button
                  key={option.type}
                  variant="outline"
                  onClick={() => {
                    setSelectedType(option.type);
                    handleSelectType(option.type);
                  }}
                  className={`flex flex-col items-start h-auto p-3 hover:border-gray-400 ${option.color} ${
                    isSelected ? 'ring-2 ring-foreground' : ''
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-4 h-4" />
                    <span className="font-medium text-sm text-foreground">
                      {option.label}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground text-left">
                    {option.description}
                  </p>
                </Button>
              );
            })}
          </div>

          {/* Shortcuts hint */}
          <div className="px-2 pt-2 border-t border-border flex items-center justify-center gap-3 text-muted-foreground text-xs">
            {needsCondition && (selectedType || preSelectedType) && (
              <>
                <span className="flex items-center gap-2">
                  <kbd className="px-2 py-1 h-5 bg-transparent text-foreground border border-gray-400 rounded text-xs font-mono flex items-center">
                    Ctrl+Enter
                  </kbd>
                  <span>Submit</span>
                </span>
                <span className="text-muted-foreground">•</span>
              </>
            )}
            <span className="flex items-center gap-2">
              <kbd className="px-2 py-1 h-5 bg-transparent text-foreground border border-gray-400 rounded text-xs font-mono flex items-center">
                Esc
              </kbd>
              <span>Close</span>
            </span>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
}
