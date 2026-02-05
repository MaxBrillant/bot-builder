import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, X } from "lucide-react";
import { ConditionSelector } from "./ConditionSelector";
import { FieldHelp } from "./FieldHelp";
import { SystemConstraints } from "@/lib/types";
import type { Route, NodeType, NodeConfig, ValidationError } from "@/lib/types";
import { cn } from "@/lib/utils";

interface RouteEditorProps {
  routes: Route[];
  availableNodes: Array<{ id: string; type: NodeType; name: string }>;
  onChange: (routes: Route[]) => void;
  errors?: ValidationError[];
  nodeType?: NodeType;
  nodeConfig?: NodeConfig; // Node configuration for context-aware conditions
  availableVariables?: string[];
}

export function RouteEditor({
  routes,
  availableNodes,
  onChange,
  errors = [],
  nodeType,
  nodeConfig,
  availableVariables = [],
}: RouteEditorProps) {
  const [inlineErrors, setInlineErrors] = useState<Record<number, string>>({});

  // Check for duplicate conditions (case-insensitive, whitespace-trimmed)
  const checkDuplicateCondition = (
    currentIndex: number,
    condition: string
  ): string | null => {
    const trimmedCondition = condition.trim();
    if (!trimmedCondition) {
      return null; // Empty conditions will be caught by required field validation
    }

    const normalizedCondition = trimmedCondition.toLowerCase();

    // Check against all other routes
    for (let i = 0; i < routes.length; i++) {
      if (i === currentIndex) continue; // Skip the current route

      const otherCondition = routes[i].condition?.trim().toLowerCase() || "";
      if (otherCondition === normalizedCondition) {
        return "This condition already exists. Each route must have a unique condition.";
      }
    }

    return null;
  };

  const handleAddRoute = () => {
    if (routes.length >= SystemConstraints.MAX_ROUTES_PER_NODE) return;

    const newRoute: Route = {
      condition: "",
      target_node: "",
    };
    onChange([...routes, newRoute]);
  };

  const handleDeleteRoute = (index: number) => {
    const newRoutes = routes.filter((_, i) => i !== index);
    onChange(newRoutes);
  };

  const handleUpdateRoute = (
    index: number,
    field: keyof Route,
    value: string
  ) => {
    // If updating condition, check for duplicates
    if (field === "condition") {
      const duplicateError = checkDuplicateCondition(index, value);

      // Update inline errors state
      setInlineErrors((prev) => {
        const newErrors = { ...prev };
        if (duplicateError) {
          newErrors[index] = duplicateError;
        } else {
          delete newErrors[index];
        }
        return newErrors;
      });
    }

    const newRoutes = [...routes];
    newRoutes[index] = { ...newRoutes[index], [field]: value };
    onChange(newRoutes);
  };

  const getRouteErrors = (index: number): ValidationError[] => {
    return errors.filter(
      (error) =>
        error.field === `routes[${index}].condition` ||
        error.field === `routes[${index}].target_node`
    );
  };


  // Get context-specific example based on node type
  const getExample = () => {
    switch (nodeType) {
      case "PROMPT":
      case "MESSAGE":
        return (
          <>
            <p className="text-xs font-medium mt-2">How it works:</p>
            <p className="mt-1 text-xs">
              This node type only has one route option: "Next". The conversation automatically continues to the target node you select.
            </p>
            <p className="text-xs font-medium mt-2">For conditional routing:</p>
            <p className="mt-1 text-xs">
              If you need to route based on the user's input (e.g., "if they said yes, go here; if no, go there"), place a Logic Expression node after this {nodeType === "PROMPT" ? "prompt" : "message"}.
            </p>
          </>
        );
      case "LOGIC_EXPRESSION":
        return (
          <>
            <p className="text-xs font-medium mt-2">How it works:</p>
            <p className="mt-1 text-xs mb-2">
              Write expressions that evaluate to true or false. The bot checks each route from top to bottom and goes to the first one where the expression is true.
            </p>
            <p className="text-xs font-medium mt-2">Example:</p>
            <ul className="list-none space-y-1 mt-1 text-xs">
              <li>• Route: context.is_member == true → Go to "Member Benefits"</li>
              <li>• Route: context.is_member == false → Go to "Sign Up"</li>
            </ul>
            <p className="text-xs font-medium mt-2">What you can use:</p>
            <p className="mt-1 text-xs">
              • <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">context.variable_name</code> - Any variable from your flow
            </p>
            <p className="mt-2 text-xs">
              All answers you collected from users are available as variables.
            </p>
          </>
        );
      default:
        return (
          <>
            <p className="text-xs font-medium mt-2">Example:</p>
            <ul className="list-none space-y-1 mt-1 text-xs">
              <li>• Route 1: If condition matches → Go to "Next Node"</li>
              <li>• Route 2: If different condition → Go to "Alternative Node"</li>
            </ul>
          </>
        );
    }
  };

  return (
    <div className="space-y-2">
      <FieldHelp
        text="Control where the conversation goes next based on conditions"
        tooltip={
          <>
            <p className="mb-2">
              Routes determine which node to go to next. Each route has a condition (the "if") and a target node (the "then"). The bot checks conditions from top to bottom and goes to the first one that matches.
            </p>
            {getExample()}
            <p className="text-xs font-medium mt-2">Auto-sorting:</p>
            <p className="mt-1 text-xs">
              Routes are automatically reordered so specific conditions are checked before general ones.
            </p>
          </>
        }
      />

      {routes.length > 0 && (
        <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start px-1">
          <div className="text-xs font-medium text-muted-foreground">
            Condition
          </div>
          <div className="text-xs font-medium text-muted-foreground">
            Target Node
          </div>
          <div className="w-9" />
        </div>
      )}
      {routes.map((route, index) => {
        const routeErrors = getRouteErrors(index);
        const inlineError = inlineErrors[index];
        const conditionError =
          inlineError ||
          routeErrors.find((e) => e.field === `routes[${index}].condition`)
            ?.message;
        const targetError = routeErrors.find(
          (e) => e.field === `routes[${index}].target_node`
        )?.message;

        return (
          <div key={index} className="space-y-1">
            <div className="grid grid-cols-[1fr_1fr_auto] gap-2 items-start">
              <div className="min-w-0">
                <ConditionSelector
                  nodeType={nodeType || "MESSAGE"}
                  nodeConfig={nodeConfig}
                  value={route.condition}
                  onChange={(value) =>
                    handleUpdateRoute(index, "condition", value)
                  }
                  error={conditionError}
                  placeholder={
                    nodeType === "MENU"
                      ? "Select menu option"
                      : nodeType === "API_ACTION"
                      ? "Select condition"
                      : nodeType === "LOGIC_EXPRESSION"
                      ? "Enter expression"
                      : "Select condition"
                  }
                  availableVariables={availableVariables}
                />
              </div>
              <div className="min-w-0">
                <Select
                  value={route.target_node}
                  onValueChange={(value) =>
                    handleUpdateRoute(index, "target_node", value)
                  }
                >
                  <SelectTrigger
                    className={cn(
                      "text-sm",
                      targetError && "border-destructive"
                    )}
                  >
                    <SelectValue placeholder="Select node" />
                  </SelectTrigger>
                  <SelectContent>
                    {availableNodes.length === 0 ? (
                      <div className="px-2 py-2 text-sm text-muted-foreground">
                        No nodes available
                      </div>
                    ) : (
                      (() => {
                        const usedTargets = new Set(
                          routes
                            .map((r, i) => (i !== index ? r.target_node : null))
                            .filter(Boolean)
                        );

                        const availableTargets = availableNodes.filter(
                          (node) =>
                            node.id === route.target_node ||
                            !usedTargets.has(node.id)
                        );

                        if (availableTargets.length === 0) {
                          return (
                            <div className="px-2 py-2 text-sm text-muted-foreground">
                              All nodes used
                            </div>
                          );
                        }

                        return availableTargets
                          .sort((a, b) => a.name.localeCompare(b.name))
                          .map((node) => (
                            <SelectItem key={node.id} value={node.id}>
                              {node.name}
                            </SelectItem>
                          ));
                      })()
                    )}
                  </SelectContent>
                </Select>
                {targetError && (
                  <p className="text-sm text-destructive mt-1">{targetError}</p>
                )}
              </div>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => handleDeleteRoute(index)}
                className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        );
      })}

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleAddRoute}
        disabled={routes.length >= SystemConstraints.MAX_ROUTES_PER_NODE}
        className="w-full"
      >
        <Plus className="h-4 w-4 mr-2" />
        Add Route ({routes.length}/{SystemConstraints.MAX_ROUTES_PER_NODE})
      </Button>
    </div>
  );
}
