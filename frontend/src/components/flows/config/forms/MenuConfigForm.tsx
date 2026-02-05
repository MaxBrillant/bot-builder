import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { ChevronRight } from "lucide-react";
import { TemplateInput } from "../shared/TemplateInput";
import { VariableSelect } from "../shared/VariableSelect";
import { StaticOptionsGrid } from "../shared/StaticOptionsGrid";
import { OutputMappingGrid } from "../shared/OutputMappingGrid";
import { InterruptsGrid } from "../shared/InterruptsGrid";
import { FieldHelp } from "../shared/FieldHelp";
import type {
  MenuNodeConfig,
  ValidationError,
  MenuSourceType,
} from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface MenuConfigFormProps {
  config: MenuNodeConfig;
  onChange: (config: MenuNodeConfig) => void;
  errors: ValidationError[];
  availableVariables?: string[];
  availableNodes?: Array<{ id: string; name: string }>;
  variables?: Array<{ name: string; type: string }>;
  onCreateVariable: (variable: {
    name: string;
    type: string;
    default: any;
  }) => Promise<void>;
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement>;
}

export function MenuConfigForm({
  config,
  onChange,
  errors,
  availableVariables,
  availableNodes,
  variables = [],
  onCreateVariable,
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
}: MenuConfigFormProps) {
  const safeAvailableVariables = availableVariables ?? [];
  const safeAvailableNodes = availableNodes ?? [];

  // Collapsible state - ALL start collapsed
  const [isOptionsOpen, setIsOptionsOpen] = useState(false);
  const [isExtractDataOpen, setIsExtractDataOpen] = useState(false);
  const [isErrorMessageOpen, setIsErrorMessageOpen] = useState(false);
  const [isInterruptsOpen, setIsInterruptsOpen] = useState(false);

  // Auto-open based on config
  useEffect(() => {
    // Options open when configured
    if (
      (config.source_type === "STATIC" &&
        config.static_options &&
        config.static_options.length > 0) ||
      (config.source_type === "DYNAMIC" && config.source_variable)
    ) {
      setIsOptionsOpen(true);
    }

    // Extract Data open when configured (dynamic mode only)
    if (
      config.source_type === "DYNAMIC" &&
      config.output_mapping &&
      config.output_mapping.length > 0
    ) {
      setIsExtractDataOpen(true);
    }

    // Error message open when set
    if (config.error_message) {
      setIsErrorMessageOpen(true);
    }

    // Interrupts open when configured
    if (config.interrupts && config.interrupts.length > 0) {
      setIsInterruptsOpen(true);
    }
  }, [config]);

  // Error dictionary (API_ACTION pattern)
  const errorDict: Record<string, string> = {};
  errors.forEach((error) => {
    errorDict[error.field] = error.message;
  });

  const handleTextChange = (text: string) => {
    onChange({ ...config, type: "MENU", text });
  };

  const handleSourceTypeChange = (value: string) => {
    const source_type: MenuSourceType = value === "static" ? "STATIC" : "DYNAMIC";
    const newConfig: MenuNodeConfig = {
      type: "MENU",
      text: config.text,
      source_type,
      interrupts: config.interrupts,
    };

    if (source_type === "STATIC") {
      newConfig.static_options = config.static_options || [];
    } else {
      newConfig.source_variable = config.source_variable || "";
      newConfig.item_template = config.item_template || "";
      newConfig.output_mapping = config.output_mapping || [];
    }

    onChange(newConfig);
  };

  const handleStaticOptionsChange = (
    static_options: typeof config.static_options
  ) => {
    onChange({ ...config, type: "MENU", static_options });
  };

  const handleSourceVariableChange = (source_variable: string) => {
    onChange({ ...config, type: "MENU", source_variable });
  };

  const handleItemTemplateChange = (item_template: string) => {
    onChange({ ...config, type: "MENU", item_template });
  };

  const handleOutputMappingChange = (
    output_mapping: typeof config.output_mapping
  ) => {
    onChange({ ...config, type: "MENU", output_mapping });
  };

  const handleErrorMessageChange = (error_message: string) => {
    onChange({ ...config, type: "MENU", error_message });
  };

  const handleInterruptsChange = (interrupts: typeof config.interrupts) => {
    onChange({ ...config, type: "MENU", interrupts });
  };

  const showDynamic = config.source_type === "DYNAMIC";

  return (
    <div>
      {/* Node Name */}
      {nodeName !== undefined && onNodeNameChange && (
        <div className="space-y-2 mb-4">
          <Input
            ref={nodeNameInputRef}
            value={nodeName}
            onChange={(e) => onNodeNameChange(e.target.value)}
            placeholder="Enter node name"
            maxLength={50}
            className={cn(
              nodeNameError && "border-destructive focus-visible:ring-destructive"
            )}
          />
          {nodeNameError && (
            <p className="text-sm text-destructive">{nodeNameError}</p>
          )}
        </div>
      )}

      {nodeName !== undefined && onNodeNameChange && <Separator />}

      {/* Menu */}
      <div className={cn(nodeName !== undefined && "mt-4", "mb-4")}>
        {/* Section Title */}
        {nodeName !== undefined && onNodeNameChange && (
          <span className="text-sm font-semibold text-foreground block mb-3">
            Configuration
          </span>
        )}

        <div className="space-y-3">
          {/* Menu Text */}
          <TemplateInput
            value={config.text ?? ""}
            onChange={handleTextChange}
            error={errorDict["text"]}
            maxLength={SystemConstraints.MAX_MESSAGE_LENGTH}
            placeholder="Enter the menu prompt"
            rows={2}
            availableVariables={safeAvailableVariables}
            nodeType="MENU"
          />

          {/* Options Type */}
          <div className="space-y-1">
            <Select
              value={config.source_type === "STATIC" ? "static" : "dynamic"}
              onValueChange={handleSourceTypeChange}
            >
              <SelectTrigger
                className={cn(errorDict["source_type"] && "border-destructive")}
              >
                <SelectValue placeholder="Select options type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="static">Static menu</SelectItem>
                <SelectItem value="dynamic">Dynamic menu</SelectItem>
              </SelectContent>
            </Select>
            {errorDict["source_type"] && (
              <p className="text-sm text-destructive">
                {errorDict["source_type"]}
              </p>
            )}
            <FieldHelp
              text="Choose between fixed options or options from data"
              tooltip={
                <>
                  <p className="mb-2"><strong>Static menu</strong> - You manually type the menu choices that never change.</p>
                  <p className="mt-1 text-xs mb-2">
                    Use this when your menu is always the same. For example: "1. Contact Support, 2. Check Status, 3. Cancel Order"
                  </p>

                  <p className="mb-2 mt-3"><strong>Dynamic menu</strong> - Menu options come from data stored in a variable (usually from an API call).</p>
                  <p className="mt-1 text-xs mb-2">
                    Use this when options change based on data. For example: showing a list of available products, user's orders, or search results from an API.
                  </p>

                  <p className="text-xs font-medium mt-3">When to use dynamic:</p>
                  <p className="mt-1 text-xs">
                    • Menu items come from an API<br />
                    • Options are different for each user<br />
                    • List changes frequently
                  </p>
                </>
              }
            />
          </div>
        </div>
      </div>

      <Separator />

      {/* Options Collapsible */}
      <Collapsible
        open={isOptionsOpen}
        onOpenChange={setIsOptionsOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isOptionsOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">
              Menu Options
            </span>
            {config.source_type === "STATIC" &&
              config.static_options &&
              config.static_options.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {config.static_options.length}
                </Badge>
              )}
            {config.source_type === "DYNAMIC" && config.source_variable && (
              <Badge variant="secondary" className="text-xs">
                ✓
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-7">
            {/* Static Options - Inline Grid */}
            {!showDynamic && (
              <StaticOptionsGrid
                value={config.static_options || []}
                onChange={handleStaticOptionsChange}
                errors={errorDict}
                availableVariables={safeAvailableVariables}
              />
            )}

            {/* Dynamic Options */}
            {showDynamic && (
              <>
                {/* Source Variable */}
                <div className="space-y-1">
                  <Label htmlFor="source-variable" className="text-xs">
                    Source Variable
                  </Label>
                  <VariableSelect
                    value={config.source_variable || ""}
                    onValueChange={handleSourceVariableChange}
                    variables={variables}
                    onCreateVariable={onCreateVariable}
                    placeholder="Select array variable"
                    typeFilter="array"
                    className={cn(
                      "font-mono",
                      errorDict["source_variable"] && "border-destructive"
                    )}
                  />
                  {errorDict["source_variable"] && (
                    <p className="text-sm text-destructive">
                      {errorDict["source_variable"]}
                    </p>
                  )}
                  <FieldHelp
                    text="Variable containing the list of menu items (array type)"
                    tooltip={
                      <>
                        <p className="mb-2">
                          This should be a variable that holds a list of items (an array). Each item in the list becomes one menu option that users can select by typing its number.
                        </p>
                        <p className="text-xs font-medium mt-2">Where does this come from?</p>
                        <p className="mt-1 text-xs mb-2">
                          Typically from an API Action node. For example, if an API returns a list of products, orders, or search results, store that in a variable and use it here.
                        </p>
                        <p className="text-xs font-medium mt-2">
                          Example data in the variable:
                        </p>
                        <pre className="mt-1 text-xs bg-primary-foreground text-primary p-2 rounded overflow-x-auto">
                          {`[
  {"id": 1, "name": "Basic Plan", "price": 10},
  {"id": 2, "name": "Pro Plan", "price": 25}
]`}
                        </pre>
                        <p className="text-xs mt-2">
                          With this data, the menu will show 2 options that users can select.
                        </p>
                      </>
                    }
                  />
                </div>

                {/* Item Template */}
                <div className="space-y-1">
                  <Label htmlFor="item-template" className="text-xs">
                    Display Format
                  </Label>
                  <TemplateInput
                    value={config.item_template || ""}
                    onChange={handleItemTemplateChange}
                    error={errorDict["item_template"]}
                    maxLength={SystemConstraints.MAX_TEMPLATE_LENGTH}
                    placeholder="{{index}}. {{item.name}}"
                    rows={2}
                    availableVariables={safeAvailableVariables}
                    nodeType="MENU"
                    fieldContext="item_template"
                  />
                  <FieldHelp
                    text="How each menu option should be displayed to the user"
                    tooltip={
                      <>
                        <p className="mb-2">
                          Design how each menu item appears. You can include data from each item in your array using the template syntax.
                        </p>
                        <p className="text-xs font-medium mt-2">Available placeholders:</p>
                        <p className="mt-1 text-xs">
                          • <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">{"{{index}}"}</code> - The option number (1, 2, 3, etc.)
                        </p>
                        <p className="mt-1 text-xs mb-2">
                          • <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">{"{{item.fieldname}}"}</code> - Data from each item (replace "fieldname" with actual field names)
                        </p>
                        <p className="text-xs font-medium mt-2">Example:</p>
                        <p className="mt-1 text-xs">
                          If your data has "name" and "price" fields, use:
                        </p>
                        <p className="mt-1 text-xs">
                          <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">
                            {"{{index}}. {{item.name}} - ${{item.price}}"}
                          </code>
                        </p>
                        <p className="mt-1 text-xs">
                          This displays: "1. Pro Plan - $25"
                        </p>
                        <p className="text-xs font-medium mt-2">Note:</p>
                        <p className="mt-1 text-xs">
                          Array length ({"{{items.length}}"}) doesn't work in templates. Check the array length using a Logic Expression node instead.
                        </p>
                      </>
                    }
                  />
                </div>
              </>
            )}
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* Extract Data Collapsible (Dynamic mode only) */}
      {showDynamic && (
        <>
        <Collapsible
          open={isExtractDataOpen}
          onOpenChange={setIsExtractDataOpen}
        >
          <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={cn(
                  "h-4 w-4 text-muted-foreground transition-transform duration-200",
                  isExtractDataOpen && "rotate-90"
                )}
              />
              <span className="text-sm font-semibold text-foreground">
                Extract Data
              </span>
              {config.output_mapping && config.output_mapping.length > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {config.output_mapping.length}
                </Badge>
              )}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="py-3 space-y-3">
              <OutputMappingGrid
                value={config.output_mapping || []}
                onChange={handleOutputMappingChange}
                errors={errorDict}
                variables={variables}
                onCreateVariable={onCreateVariable}
              />
            </div>
          </CollapsibleContent>
        </Collapsible>
        <Separator />
        </>
      )}

      {/* Error Message Collapsible */}
      <Collapsible
        open={isErrorMessageOpen}
        onOpenChange={setIsErrorMessageOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isErrorMessageOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">
              Error Message
            </span>
            {config.error_message && (
              <Badge variant="secondary" className="text-xs">
                ✓
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-3">
            <TemplateInput
              value={config.error_message ?? ""}
              onChange={handleErrorMessageChange}
              error={errorDict["error_message"]}
              maxLength={SystemConstraints.MAX_ERROR_MESSAGE_LENGTH}
              placeholder="Invalid selection. Please try again."
              rows={2}
              availableVariables={safeAvailableVariables}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* Interrupts Collapsible */}
      <Collapsible
        open={isInterruptsOpen}
        onOpenChange={setIsInterruptsOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isInterruptsOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">
              Escape Keys
            </span>
            {config.interrupts && config.interrupts.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {config.interrupts.length}
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-3">
            <InterruptsGrid
              value={config.interrupts || []}
              onChange={handleInterruptsChange}
              availableNodes={safeAvailableNodes}
              errors={errorDict}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
