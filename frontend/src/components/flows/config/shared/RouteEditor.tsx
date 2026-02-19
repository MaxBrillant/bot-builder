import { useState } from "react";
import { ListEditor, type FieldDefinition, type CustomFieldProps } from "./list-editor";
import { ConditionSelector } from "./ConditionSelector";
import { SystemConstraints } from "@/lib/types";
import type { Route, NodeType, NodeConfig, ValidationError } from "@/lib/types";

interface RouteEditorProps {
  routes: Route[];
  availableNodes: Array<{ id: string; type: NodeType; name: string }>;
  onChange: (routes: Route[]) => void;
  errors?: ValidationError[];
  nodeType?: NodeType;
  nodeConfig?: NodeConfig;
  availableVariables?: string[];
}

function formatCondition(condition: string): string {
  if (!condition) return "";
  if (condition === "true" || condition === "default") return "Always";
  if (condition === "next") return "Next";
  // For menu options like "option_1", "option_2"
  if (condition.startsWith("option_")) {
    const num = condition.replace("option_", "");
    return `Option ${num}`;
  }
  // For API status codes
  if (condition.startsWith("status_")) {
    return condition.replace("status_", "Status ");
  }
  // Truncate long conditions
  if (condition.length > 30) {
    return condition.substring(0, 27) + "...";
  }
  return condition;
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

  // Check for duplicate conditions
  const checkDuplicateCondition = (
    currentIndex: number,
    condition: string
  ): string | null => {
    const trimmedCondition = condition.trim();
    if (!trimmedCondition) return null;

    const normalizedCondition = trimmedCondition.toLowerCase();
    for (let i = 0; i < routes.length; i++) {
      if (i === currentIndex) continue;
      const otherCondition = routes[i].condition?.trim().toLowerCase() || "";
      if (otherCondition === normalizedCondition) {
        return "This condition already exists. Each route must have a unique condition.";
      }
    }
    return null;
  };

  // Convert ValidationError[] to Record<string, string> for ListEditor
  const errorsRecord: Record<string, string> = {};
  errors.forEach((error) => {
    errorsRecord[error.field] = error.message;
  });
  // Merge inline errors
  Object.entries(inlineErrors).forEach(([index, msg]) => {
    errorsRecord[`routes[${index}].condition`] = msg;
  });

  const handleChange = (newRoutes: Route[]) => {
    // Check for duplicate conditions
    const newInlineErrors: Record<number, string> = {};
    newRoutes.forEach((route, index) => {
      const duplicateError = checkDuplicateCondition(index, route.condition);
      if (duplicateError) {
        newInlineErrors[index] = duplicateError;
      }
    });
    setInlineErrors(newInlineErrors);
    onChange(newRoutes);
  };

  // Dynamic options function that filters out already-used target nodes
  const getAvailableTargetNodes = (currentRoute: Route, context: Record<string, unknown>) => {
    const allRoutes = context.routes as Route[];
    const usedTargets = new Set(
      allRoutes
        .filter((r) => r.target_node && r.target_node !== currentRoute.target_node)
        .map((r) => r.target_node)
    );

    return availableNodes
      .filter((node) => node.id === currentRoute.target_node || !usedTargets.has(node.id))
      .sort((a, b) => a.name.localeCompare(b.name))
      .map((node) => ({ value: node.id, label: node.name }));
  };

  const fields: FieldDefinition<Route>[] = [
    {
      key: "condition",
      label: "Condition",
      type: "custom",
      render: ({ value, onChange, error }: CustomFieldProps<Route>) => (
        <ConditionSelector
          nodeType={nodeType || "TEXT"}
          nodeConfig={nodeConfig}
          value={(value as string) ?? ""}
          onChange={onChange}
          error={error}
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
      ),
    },
    {
      key: "target_node",
      label: "Target Node",
      type: "select",
      placeholder: "Select node",
      options: getAvailableTargetNodes,
    },
  ];

  // Get context-specific help
  const getHelpContent = () => {
    switch (nodeType) {
      case "PROMPT":
      case "TEXT":
        return (
          <>
            <p className="text-xs font-medium mt-2">How it works:</p>
            <p className="mt-1 text-xs">
              This node type only has one route option: "Next". The conversation automatically continues to the target node you select.
            </p>
            <p className="text-xs font-medium mt-2">For conditional routing:</p>
            <p className="mt-1 text-xs">
              If you need to route based on the user's input, place a Logic node after this {nodeType === "PROMPT" ? "prompt" : "message"}.
            </p>
          </>
        );
      case "LOGIC_EXPRESSION":
        return (
          <>
            <p className="text-xs font-medium mt-2">How it works:</p>
            <p className="mt-1 text-xs mb-2">
              Build conditions using the dropdowns. The bot checks each route and follows the first one where the condition is true.
            </p>
            <p className="text-xs font-medium mt-2">Example:</p>
            <ul className="list-none space-y-1 mt-1 text-xs">
              <li>• If "is_member" equals "true" → Go to "Member Benefits"</li>
              <li>• Always match (fallback) → Go to "Sign Up"</li>
            </ul>
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
    <ListEditor
      items={routes}
      onChange={handleChange}
      fields={fields}
      createEmpty={() => ({ condition: "", target_node: "" })}
      renderColumns={(route) => {
        const nodeName = availableNodes.find(
          (n) => n.id === route.target_node
        )?.name;
        return [
          <span key="condition" className="text-xs">
            {formatCondition(route.condition) || (
              <span className="text-muted-foreground">condition</span>
            )}
          </span>,
          <span key="node" className="text-xs">
            {nodeName || <span className="text-muted-foreground">node</span>}
          </span>,
        ];
      }}
      listHeaders={["Condition", "Target Node"]}
      maxItems={SystemConstraints.MAX_ROUTES_PER_NODE}
      addLabel="Add Route"
      errorPrefix="routes"
      errors={errorsRecord}
      helpText="Choose where the conversation goes next"
      helpTooltip={
        <>
          <p className="mb-2">
            Routes decide which node comes next in the conversation. Think of it like "if this, then go there". The bot checks each route in order and follows the first one that matches.
          </p>
          {getHelpContent()}
          <p className="text-xs font-medium mt-2">Good to know:</p>
          <p className="mt-1 text-xs">
            Routes are automatically ordered so specific choices (like "option 1") are checked before general ones (like "always go here").
          </p>
        </>
      }
      editorSide="left"
      context={{ routes }}
    />
  );
}
