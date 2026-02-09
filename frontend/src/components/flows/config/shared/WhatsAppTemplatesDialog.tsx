/**
 * WhatsApp Templates Dialog
 *
 * Allows users to select pre-configured WhatsApp integration templates
 * to auto-populate API_ACTION nodes
 */

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  Image,
  Mic,
  MoreHorizontal,
  CheckCheck,
  MapPin,
  Contact,
  Users,
  Info,
  List,
  FolderPlus,
  UserPlus,
  UserMinus,
  Shield,
  ShieldOff,
  Edit,
  FileText,
  Link,
  LogOut,
  UserCheck,
  ExternalLink,
  type LucideIcon,
} from "lucide-react";
import {
  whatsappTemplates,
  type WhatsAppTemplate,
  EVOLUTION_API_POSTMAN_URL,
} from "@/lib/whatsappTemplates";
import type { APIActionNodeConfig } from "@/lib/types";
import { cn } from "@/lib/utils";

// Icon mapping for templates
const iconMap: Record<string, LucideIcon> = {
  MessageSquare,
  Image,
  Mic,
  MoreHorizontal,
  CheckCheck,
  MapPin,
  Contact,
  Users,
  Info,
  List,
  FolderPlus,
  UserPlus,
  UserMinus,
  Shield,
  ShieldOff,
  Edit,
  FileText,
  Link,
  LogOut,
  UserCheck,
};

function getIcon(iconName: string): LucideIcon {
  return iconMap[iconName] || MessageSquare;
}

interface WhatsAppTemplatesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectTemplate: (config: APIActionNodeConfig) => void;
  botId?: string;
}

export function WhatsAppTemplatesDialog({
  open,
  onOpenChange,
  onSelectTemplate,
  botId,
}: WhatsAppTemplatesDialogProps) {
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  const handleTemplateClick = (template: WhatsAppTemplate) => {
    setSelectedTemplateId(template.id);
  };

  const handleApply = () => {
    const template = whatsappTemplates.find((t) => t.id === selectedTemplateId);
    if (template) {
      // Deep clone the config
      const config = JSON.parse(JSON.stringify(template.config)) as APIActionNodeConfig;

      // Set bot ID in X-Bot-ID header
      if (botId && config.request?.headers) {
        const botIdHeader = config.request.headers.find(h => h.name === "X-Bot-ID");
        if (botIdHeader) {
          botIdHeader.value = botId;
        }
      }

      onSelectTemplate(config);
      onOpenChange(false);
      setSelectedTemplateId(null);
    }
  };

  const handleCancel = () => {
    onOpenChange(false);
    setSelectedTemplateId(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>WhatsApp Integration Templates</DialogTitle>
          <DialogDescription>
            Select a template to auto-populate the API action configuration.
            You can customize the configuration after applying.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* Templates Grid - Scrollable */}
          <div className="grid grid-cols-1 gap-3 max-h-[400px] overflow-y-auto pr-2">
            {whatsappTemplates.map((template) => (
              <button
                key={template.id}
                onClick={() => handleTemplateClick(template)}
                className={cn(
                  "flex items-center gap-4 p-4 rounded-lg border transition-all text-left",
                  "hover:border-primary/50 hover:bg-accent/50",
                  selectedTemplateId === template.id
                    ? "border-primary bg-accent"
                    : "border-border bg-background"
                )}
              >
                {/* Icon */}
                <div className={cn(
                  "flex items-center justify-center w-10 h-10 rounded-lg shrink-0",
                  selectedTemplateId === template.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground"
                )}>
                  {(() => {
                    const Icon = getIcon(template.icon);
                    return <Icon className="w-5 h-5" />;
                  })()}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-sm">
                    {template.name}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {template.description}
                  </p>
                </div>
              </button>
            ))}
          </div>

          {/* Empty state if no templates */}
          {whatsappTemplates.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p>No templates available</p>
            </div>
          )}

          {/* Evolution API Note */}
          <div className="rounded-lg bg-muted/50 p-3 text-sm text-muted-foreground">
            <p>
              Need a different request? You can execute any Evolution API endpoint
              by configuring a custom API action.{" "}
              <a
                href={EVOLUTION_API_POSTMAN_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-primary hover:underline"
              >
                View full API docs
                <ExternalLink className="w-3 h-3" />
              </a>
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <Button variant="outline" onClick={handleCancel}>
              Cancel
            </Button>
            <Button
              onClick={handleApply}
              disabled={!selectedTemplateId}
            >
              Apply Template
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
