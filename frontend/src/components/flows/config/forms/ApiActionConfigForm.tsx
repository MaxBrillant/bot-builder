import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
import { ChevronRight, Terminal } from "lucide-react";
import { TemplateInput } from "../shared/TemplateInput";
import { HeadersEditor } from "../shared/HeadersEditor";
import { JsonBodyEditor } from "../shared/JsonBodyEditor";
import { ResponseMappingEditor } from "../shared/ResponseMappingEditor";
import { SuccessCheckEditor } from "../shared/SuccessCheckEditor";
import { FieldHelp } from "../shared/FieldHelp";
import { WhatsAppTemplatesDialog } from "../shared/WhatsAppTemplatesDialog";
import { CurlImportDialog } from "../shared/CurlImportDialog";
import type {
  APIActionNodeConfig,
  ValidationError,
  HTTPMethod,
  APIHeader,
  VariableType,
} from "@/lib/types";
import { SystemConstraints } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ApiActionConfigFormProps {
  config: APIActionNodeConfig;
  onChange: (config: APIActionNodeConfig) => void;
  errors: ValidationError[];
  availableVariables?: string[];
  variables?: Array<{ name: string; type: VariableType }>;
  onCreateVariable: (variable: {
    name: string;
    type: VariableType;
    default: any;
  }) => Promise<void>;
  nodeName?: string;
  onNodeNameChange?: (name: string) => void;
  nodeNameError?: string;
  nodeNameInputRef?: React.RefObject<HTMLInputElement | null>;
  botId?: string;
}

export function ApiActionConfigForm({
  config,
  onChange,
  errors,
  availableVariables,
  variables = [],
  onCreateVariable,
  nodeName,
  onNodeNameChange,
  nodeNameError,
  nodeNameInputRef,
  botId,
}: ApiActionConfigFormProps) {
  // Safely handle undefined/null availableVariables
  const safeAvailableVariables = availableVariables ?? [];

  // Collapsible sections state
  const [isRequestHeadersOpen, setIsRequestHeadersOpen] = useState(false);
  const [isRequestBodyOpen, setIsRequestBodyOpen] = useState(false);
  const [isResponseMappingOpen, setIsResponseMappingOpen] = useState(false);
  const [isSuccessCheckOpen, setIsSuccessCheckOpen] = useState(false);

  // WhatsApp templates dialog state
  const [isWhatsAppDialogOpen, setIsWhatsAppDialogOpen] = useState(false);

  // cURL import dialog state
  const [isCurlDialogOpen, setIsCurlDialogOpen] = useState(false);

  // Auto-open logic based on config
  useEffect(() => {
    // Request Headers open when headers exist
    if (
      config.request?.headers &&
      Array.isArray(config.request.headers) &&
      config.request.headers.length > 0
    ) {
      setIsRequestHeadersOpen(true);
    }

    // Request Body open when body is set
    if (config.request?.body) {
      setIsRequestBodyOpen(true);
    }

    // Response Mapping open when mapping exists
    if (config.response_map && config.response_map.length > 0) {
      setIsResponseMappingOpen(true);
    }

    // Success Check open when configured
    if (config.success_check) {
      setIsSuccessCheckOpen(true);
    }
  }, [config]);


  const handleMethodChange = (method: HTTPMethod) => {
    onChange({
      ...config,
      type: "API_ACTION",
      request: {
        ...config.request,
        method,
      },
    });
  };

  const handleUrlChange = (url: string) => {
    onChange({
      ...config,
      type: "API_ACTION",
      request: {
        ...config.request,
        url,
      },
    });
  };

  const handleHeadersChange = (headers: APIHeader[]) => {
    onChange({
      ...config,
      type: "API_ACTION",
      request: {
        ...config.request,
        headers: headers.length > 0 ? headers : undefined,
      },
    });
  };

  const handleBodyChange = (body: any) => {
    onChange({
      ...config,
      type: "API_ACTION",
      request: {
        ...config.request,
        body,
      },
    });
  };

  const handleResponseMapChange = (response_map: any[]) => {
    onChange({
      ...config,
      type: "API_ACTION",
      response_map: response_map.length > 0 ? response_map : undefined,
    });
  };

  const handleSuccessCheckChange = (success_check: any) => {
    onChange({
      ...config,
      type: "API_ACTION",
      success_check,
    });
  };

  // Get errors as a dictionary for easier lookup
  const errorDict: Record<string, string> = {};
  errors.forEach((error) => {
    errorDict[error.field] = error.message;
  });

  // Check if body should be shown (only for POST, PUT, PATCH)
  const showBody = ["POST", "PUT", "PATCH"].includes(
    config.request?.method ?? "GET"
  );

  // Handle WhatsApp template selection - merge with existing config
  const handleWhatsAppTemplateSelect = (templateConfig: APIActionNodeConfig) => {
    onChange({
      ...config,
      ...templateConfig,
      // Preserve existing response_map and success_check if not in template
      response_map: templateConfig.response_map ?? config.response_map,
      success_check: templateConfig.success_check ?? config.success_check,
    });
  };

  // Handle cURL import - merge with existing config
  const handleCurlImport = (importedConfig: APIActionNodeConfig) => {
    onChange({
      ...config,
      ...importedConfig,
      // Preserve existing response_map and success_check
      response_map: config.response_map,
      success_check: config.success_check,
    });
  };

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

      {/* Core Action */}
      <div className={cn(nodeName !== undefined && "mt-4", "mb-4")}>
        {/* Section Title with Quick Import Buttons */}
        {nodeName !== undefined && onNodeNameChange && (
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-foreground">
              Configuration
            </span>
            <div className="flex items-center gap-1">
              {/* cURL Import Button */}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsCurlDialogOpen(true)}
                className="h-7 w-7 p-0"
                title="Import from cURL"
              >
                <Terminal className="w-4 h-4" />
              </Button>
              {/* WhatsApp Template Button */}
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setIsWhatsAppDialogOpen(true)}
                className="h-7 w-7 p-0"
                title="Use WhatsApp Template"
              >
                {/* WhatsApp Icon */}
                <svg
                  viewBox="0 0 24 24"
                  fill="currentColor"
                  className="w-4 h-4"
                >
                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413Z"/>
                </svg>
              </Button>
            </div>
          </div>
        )}

        <div className="space-y-3">
        {/* HTTP Method */}
        <div className="space-y-2">
          <Select
            value={config.request?.method ?? "GET"}
            onValueChange={handleMethodChange}
          >
            <SelectTrigger
              className={cn(
                errorDict["request.method"] && "border-destructive"
              )}
            >
              <SelectValue placeholder="Select HTTP method" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="GET">GET</SelectItem>
              <SelectItem value="POST">POST</SelectItem>
              <SelectItem value="PUT">PUT</SelectItem>
              <SelectItem value="DELETE">DELETE</SelectItem>
              <SelectItem value="PATCH">PATCH</SelectItem>
            </SelectContent>
          </Select>
          {errorDict["request.method"] && (
            <p className="text-sm text-destructive">{errorDict["request.method"]}</p>
          )}
        </div>

        {/* URL */}
        <TemplateInput
          value={config.request?.url ?? ""}
          onChange={handleUrlChange}
          error={errorDict["request.url"]}
          maxLength={SystemConstraints.MAX_REQUEST_URL_LENGTH}
          placeholder="https://api.example.com/{{user_id}}"
          rows={1}
          maxRows={10}
          availableVariables={safeAvailableVariables}
          nodeType="API_ACTION"
        />
        </div>
      </div>

      <Separator />

      {/* Request Headers Collapsible */}
      <Collapsible
        open={isRequestHeadersOpen}
        onOpenChange={setIsRequestHeadersOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isRequestHeadersOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">Request Headers</span>
            {config.request?.headers && config.request.headers.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {config.request.headers.length}
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-3">
            <HeadersEditor
              value={config.request?.headers ?? []}
              onChange={handleHeadersChange}
              errors={errorDict}
              availableVariables={safeAvailableVariables}
              nodeType="API_ACTION"
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* Request Body Collapsible */}
      {showBody && (
        <>
        <Collapsible
          open={isRequestBodyOpen}
          onOpenChange={setIsRequestBodyOpen}
        >
          <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
            <div className="flex items-center gap-2">
              <ChevronRight
                className={cn(
                  "h-4 w-4 text-muted-foreground transition-transform duration-200",
                  isRequestBodyOpen && "rotate-90"
                )}
              />
              <span className="text-sm font-semibold text-foreground">Request Body</span>
              {config.request?.body && (
                <Badge variant="secondary" className="text-xs">
                  ✓
                </Badge>
              )}
            </div>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="py-3 space-y-3">
              <div className="space-y-1">
                <JsonBodyEditor
                  value={config.request?.body}
                  onChange={handleBodyChange}
                  error={errorDict["request.body"]}
                  availableVariables={safeAvailableVariables}
                  nodeType="API_ACTION"
                />
                <FieldHelp
                  text="Valid JSON required. Use {{variables}} for dynamic values"
                  tooltip={
                    <>
                      <p className="mb-2">
                        The data sent to the API in JSON format. Wrap template variables in quotes. Variable types are preserved automatically.
                      </p>
                      <p className="text-xs font-medium mt-2">Example:</p>
                      <pre className="mt-1 text-xs bg-primary-foreground text-primary p-2 rounded overflow-x-auto">
                        {`{
  "user_id": "{{user_id}}",
  "amount": "{{amount}}"
}`}
                      </pre>
                    </>
                  }
                />
              </div>
            </div>
          </CollapsibleContent>
        </Collapsible>
        <Separator />
        </>
      )}

      {/* Response Mapping Collapsible */}
      <Collapsible
        open={isResponseMappingOpen}
        onOpenChange={setIsResponseMappingOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isResponseMappingOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">Extract Data</span>
            {config.response_map && config.response_map.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {config.response_map.length}
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-3">
            <ResponseMappingEditor
              value={config.response_map ?? []}
              onChange={handleResponseMapChange}
              errors={errorDict}
              variables={variables}
              onCreateVariable={onCreateVariable}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      <Separator />

      {/* Success Check Collapsible */}
      <Collapsible
        open={isSuccessCheckOpen}
        onOpenChange={setIsSuccessCheckOpen}
      >
        <CollapsibleTrigger className="flex w-full items-center justify-between py-4 hover:bg-muted/30 transition-colors">
          <div className="flex items-center gap-2">
            <ChevronRight
              className={cn(
                "h-4 w-4 text-muted-foreground transition-transform duration-200",
                isSuccessCheckOpen && "rotate-90"
              )}
            />
            <span className="text-sm font-semibold text-foreground">Success Check</span>
            {config.success_check && (
              <Badge variant="secondary" className="text-xs">
                ✓
              </Badge>
            )}
          </div>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="py-3 space-y-7">
            <SuccessCheckEditor
              value={config.success_check}
              onChange={handleSuccessCheckChange}
              errors={errorDict}
              availableVariables={safeAvailableVariables}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* WhatsApp Templates Dialog */}
      <WhatsAppTemplatesDialog
        open={isWhatsAppDialogOpen}
        onOpenChange={setIsWhatsAppDialogOpen}
        onSelectTemplate={handleWhatsAppTemplateSelect}
        botId={botId}
      />

      {/* cURL Import Dialog */}
      <CurlImportDialog
        open={isCurlDialogOpen}
        onOpenChange={setIsCurlDialogOpen}
        onImport={handleCurlImport}
      />
    </div>
  );
}
