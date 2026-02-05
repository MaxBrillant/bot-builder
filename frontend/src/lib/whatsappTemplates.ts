/**
 * WhatsApp Integration Templates
 *
 * Pre-configured API_ACTION templates for common WhatsApp operations
 * via Evolution API proxy
 */

import type { APIActionNodeConfig } from "./types";

// Get API base URL from environment
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface WhatsAppTemplate {
  id: string;
  name: string;
  description: string;
  icon: string;
  category: "messaging" | "settings" | "advanced";
  config: APIActionNodeConfig;
}

/**
 * WhatsApp integration templates
 * Users can select these to auto-populate API_ACTION nodes
 */
export const whatsappTemplates: WhatsAppTemplate[] = [
  {
    id: "send-text-message",
    name: "Send Text Message",
    description: "Send a WhatsApp text message to a user",
    icon: "MessageSquare",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/message/sendText`,
        headers: [
          {
            name: "Content-Type",
            value: "application/json"
          },
          {
            name: "X-Bot-ID",
            value: ""
          }
        ],
        body: JSON.stringify({
          number: "{{user.channel_id}}",
          text: "Hello"
        }, null, 2)
      },
      success_check: {
        status_codes: [200, 201]
      }
    }
  },
  // Future templates can be added here:
  // {
  //   id: "send-image",
  //   name: "Send Image",
  //   description: "Send an image with optional caption",
  //   icon: "Image",
  //   category: "messaging",
  //   config: { ... }
  // },
  // {
  //   id: "send-audio",
  //   name: "Send Audio",
  //   description: "Send an audio file",
  //   icon: "Mic",
  //   category: "messaging",
  //   config: { ... }
  // },
  // {
  //   id: "update-settings",
  //   name: "Update Bot Settings",
  //   description: "Configure bot behavior (auto-reply, reject calls, etc.)",
  //   icon: "Settings",
  //   category: "settings",
  //   config: { ... }
  // },
];

/**
 * Get template by ID
 */
export function getWhatsAppTemplate(id: string): WhatsAppTemplate | undefined {
  return whatsappTemplates.find((t) => t.id === id);
}

/**
 * Get templates by category
 */
export function getWhatsAppTemplatesByCategory(
  category: WhatsAppTemplate["category"]
): WhatsAppTemplate[] {
  return whatsappTemplates.filter((t) => t.category === category);
}

/**
 * Apply template to node config
 *
 * This function takes a template and returns a deep clone of the config
 */
export function applyWhatsAppTemplate(templateId: string): APIActionNodeConfig | null {
  const template = getWhatsAppTemplate(templateId);
  if (!template) return null;

  // Deep clone the config to avoid mutating the original
  const config = JSON.parse(JSON.stringify(template.config)) as APIActionNodeConfig;

  return config;
}
