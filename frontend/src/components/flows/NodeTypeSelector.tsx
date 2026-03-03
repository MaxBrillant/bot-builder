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
import { FieldHelp } from "./config/shared/FieldHelp";
import { getDefaultCondition, isBranchingNode } from "@/lib/routeConditionUtils";
import type { NodeType, FlowNode, VariableInfo } from "@/lib/types";

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
    type: "TEXT",
    label: "Text",
    icon: MessageCircle,
    description: "Display text",
    color: "text-node-text hover:bg-accent",
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
  conditionReadOnly?: boolean; // Show condition for context but don't allow editing
  availableVariables?: VariableInfo[]; // Available variables for autocomplete
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
  conditionReadOnly = false,
  availableVariables = [],
}: NodeTypeSelectorProps) {
  const [condition, setCondition] = useState("");
  const [error, setError] = useState("");
  const [selectedType, setSelectedType] = useState<NodeType | undefined>(preSelectedType);

  // Check if we need to show condition input
  // Branching nodes need conditions, except dynamic menus which have a single "true" route
  const needsCondition =
    parentNode && isBranchingNode(parentNode.type, parentNode.config);

  // Update selected type when preSelectedType changes
  useEffect(() => {
    setSelectedType(preSelectedType);
  }, [preSelectedType]);

  // Initialize condition: use pre-filled value from edge, or smart default (except for LOGIC_EXPRESSION)
  useEffect(() => {
    if (needsCondition && parentNode) {
      if (preFilledCondition) {
        setCondition(preFilledCondition);
      } else if (parentNode.type !== "LOGIC_EXPRESSION") {
        // Only set smart default for MENU and API_ACTION, not for LOGIC_EXPRESSION
        const defaultCond = getDefaultCondition(
          parentNode,
          parentNode.routes || []
        );
        setCondition(defaultCond);
      } else {
        setCondition("");
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
  // Implicit save: if condition changed and we have an update handler, save it (only when not read-only)
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      // Check if condition was modified from original
      const trimmedCondition = condition.trim();
      const originalCondition = preFilledCondition?.trim() || "";
      const conditionChanged = trimmedCondition && trimmedCondition !== originalCondition;

      // Implicit save on close if condition changed (only when editable)
      if (!conditionReadOnly && conditionChanged && onUpdateCondition) {
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
      <PopoverContent
        className="w-80 p-2 bg-background max-h-[90vh] overflow-y-auto"
        align="start"
        side="right"
        sideOffset={8}
        collisionPadding={16}
        avoidCollisions={true}
        onKeyDown={(e) => {
          // Stop propagation to prevent global keyboard handler from intercepting
          // Allow Escape to bubble so the popover can close
          if (e.key !== 'Escape') {
            e.stopPropagation();
          }
        }}
      >
        <div className="space-y-2">
          <div className="px-2 py-2 text-xs font-semibold text-muted-foreground uppercase">
            Select Node Type
          </div>

          {/* Condition Selector - only show for branching nodes */}
          {needsCondition && parentNode && (
            <div className="px-2 pb-2 border-b border-border space-y-1 max-h-[40vh] overflow-y-auto">
              {conditionReadOnly && (
                <div className="text-xs text-muted-foreground mb-1">
                  Inserting on route:
                </div>
              )}
              <ConditionSelector
                nodeType={parentNode.type}
                nodeConfig={parentNode.config}
                value={condition}
                onChange={(value) => {
                  if (!conditionReadOnly) {
                    setCondition(value);
                    setError("");
                  }
                }}
                onKeyDown={handleConditionKeyDown}
                error={error}
                disabled={conditionReadOnly}
                placeholder={
                  parentNode.type === "MENU"
                    ? "Select menu option"
                    : parentNode.type === "API_ACTION"
                    ? "Select condition"
                    : "e.g. age > 18"
                }
                availableVariables={availableVariables}
              />
              {!conditionReadOnly && parentNode.type === "MENU" && (
                <FieldHelp
                  text="Choose which menu option leads to this node"
                  tooltip={
                    <p className="mb-2">
                      Each menu option can lead to a different next step. Select which option should go to the node you're adding.
                    </p>
                  }
                />
              )}
              {!conditionReadOnly && parentNode.type === "API_ACTION" && (
                <FieldHelp
                  text="Choose what happens after the API call"
                  tooltip={
                    <>
                      <p className="mb-2">
                        API calls can succeed or fail. Choose which outcome should lead to the node you're adding.
                      </p>
                      <p className="text-xs font-medium mt-2">Options:</p>
                      <div className="space-y-1 mt-1">
                        <p className="text-xs"><strong>Success</strong> - API returned expected status code</p>
                        <p className="text-xs"><strong>Error</strong> - API failed or returned unexpected status</p>
                      </div>
                    </>
                  }
                />
              )}
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
