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
 *
 * Categories:
 * - messaging: Core messaging features (7 templates)
 * - advanced: Group management & utility (13 templates)
 */
export const whatsappTemplates: WhatsAppTemplate[] = [
  // ==================== MESSAGING (7) ====================

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
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            number: "{{session.channel_user_id}}",
            text: "Your message here"
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "send-media",
    name: "Send Media",
    description: "Send an image, video, or document with optional caption",
    icon: "Image",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/message/sendMedia`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            number: "{{session.channel_user_id}}",
            mediatype: "image",
            mimetype: "image/jpeg",
            caption: "Optional caption",
            media: "https://example.com/image.jpg",
            fileName: "image.jpg"
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "send-audio",
    name: "Send Audio Message",
    description: "Send a voice/audio message",
    icon: "Mic",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/message/sendWhatsAppAudio`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            number: "{{session.channel_user_id}}",
            audio: "https://example.com/audio.mp3"
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "send-typing",
    name: "Send Typing Indicator",
    description: "Show 'typing...' status to make bot feel more human",
    icon: "MoreHorizontal",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/chat/sendPresence`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            number: "{{session.channel_user_id}}",
            delay: 2000,
            presence: "composing"
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "mark-as-read",
    name: "Mark Message as Read",
    description: "Mark the user's message as read (blue checkmarks)",
    icon: "CheckCheck",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/chat/markMessageAsRead`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            readMessages: [
              {
                remoteJid: "{{session.channel_user_id}}@s.whatsapp.net",
                fromMe: false,
                id: "{{context.last_message_id}}"
              }
            ]
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "send-location",
    name: "Send Location",
    description: "Share a location with name and address",
    icon: "MapPin",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/message/sendLocation`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            number: "{{session.channel_user_id}}",
            name: "Business Name",
            address: "123 Main St, City, Country",
            latitude: -23.5505,
            longitude: -46.6333
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "send-contact",
    name: "Send Contact",
    description: "Share a contact card with phone number and details",
    icon: "Contact",
    category: "messaging",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/message/sendContact`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            number: "{{session.channel_user_id}}",
            contact: [
              {
                fullName: "Support Team",
                wuid: "559999999999",
                phoneNumber: "+55 99 9999-9999",
                organization: "Company Name"
              }
            ]
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  // ==================== GROUPS (11) ====================

  {
    id: "fetch-all-groups",
    name: "Fetch All Groups",
    description: "Get list of all groups the bot is a member of",
    icon: "Users",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "GET",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/fetchAllGroups?getParticipants=false`,
        headers: [{ name: "X-Bot-ID", value: "" }]
      },
      response_map: [{ source_path: "*", target_variable: "groups_list" }],
      success_check: { status_codes: [200] }
    }
  },

  {
    id: "get-group-info",
    name: "Get Group Info",
    description: "Get details about a specific group",
    icon: "Info",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "GET",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/findGroupInfos?groupJid={{context.group_jid}}`,
        headers: [{ name: "X-Bot-ID", value: "" }]
      },
      response_map: [
        { source_path: "subject", target_variable: "group_name" },
        { source_path: "desc", target_variable: "group_description" },
        { source_path: "size", target_variable: "group_size" }
      ],
      success_check: { status_codes: [200] }
    }
  },

  {
    id: "get-group-participants",
    name: "Get Group Participants",
    description: "List all members of a group",
    icon: "List",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "GET",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/participants?groupJid={{context.group_jid}}`,
        headers: [{ name: "X-Bot-ID", value: "" }]
      },
      response_map: [
        { source_path: "participants", target_variable: "group_members" }
      ],
      success_check: { status_codes: [200] }
    }
  },

  {
    id: "create-group",
    name: "Create Group",
    description: "Create a new WhatsApp group",
    icon: "FolderPlus",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/create`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            subject: "Group Name",
            description: "Group description",
            participants: ["559999999999", "559888888888"]
          },
          null,
          2
        )
      },
      response_map: [{ source_path: "id", target_variable: "new_group_jid" }],
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "add-group-participant",
    name: "Add Group Participant",
    description: "Add members to a group",
    icon: "UserPlus",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/updateParticipant?groupJid={{context.group_jid}}`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            action: "add",
            participants: ["{{context.phone_number}}"]
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "remove-group-participant",
    name: "Remove Group Participant",
    description: "Remove members from a group",
    icon: "UserMinus",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/updateParticipant?groupJid={{context.group_jid}}`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            action: "remove",
            participants: ["{{context.phone_number}}"]
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "promote-group-admin",
    name: "Promote to Admin",
    description: "Make a group member an admin",
    icon: "Shield",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/updateParticipant?groupJid={{context.group_jid}}`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            action: "promote",
            participants: ["{{context.phone_number}}"]
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "demote-group-admin",
    name: "Demote Admin",
    description: "Remove admin privileges from a member",
    icon: "ShieldOff",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/updateParticipant?groupJid={{context.group_jid}}`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            action: "demote",
            participants: ["{{context.phone_number}}"]
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "update-group-name",
    name: "Update Group Name",
    description: "Change the group subject/name",
    icon: "Edit",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/updateGroupSubject?groupJid={{context.group_jid}}`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            subject: "New Group Name"
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "update-group-description",
    name: "Update Group Description",
    description: "Change the group description",
    icon: "FileText",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/updateGroupDescription?groupJid={{context.group_jid}}`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            description: "New group description or rules"
          },
          null,
          2
        )
      },
      success_check: { status_codes: [200, 201] }
    }
  },

  {
    id: "get-group-invite-link",
    name: "Get Group Invite Link",
    description: "Get the invite link for a group",
    icon: "Link",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "GET",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/inviteCode?groupJid={{context.group_jid}}`,
        headers: [{ name: "X-Bot-ID", value: "" }]
      },
      response_map: [
        { source_path: "inviteCode", target_variable: "group_invite_code" },
        { source_path: "inviteUrl", target_variable: "group_invite_url" }
      ],
      success_check: { status_codes: [200] }
    }
  },

  {
    id: "leave-group",
    name: "Leave Group",
    description: "Remove the bot from a group",
    icon: "LogOut",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "DELETE",
        url: `${API_BASE_URL}/api/integrations/whatsapp/group/leaveGroup?groupJid={{context.group_jid}}`,
        headers: [{ name: "X-Bot-ID", value: "" }]
      },
      success_check: { status_codes: [200] }
    }
  },

  // ==================== UTILITY (2) ====================

  {
    id: "check-whatsapp-number",
    name: "Check WhatsApp Number",
    description: "Validate if phone numbers have WhatsApp accounts",
    icon: "UserCheck",
    category: "advanced",
    config: {
      type: "API_ACTION",
      request: {
        method: "POST",
        url: `${API_BASE_URL}/api/integrations/whatsapp/chat/whatsappNumbers`,
        headers: [
          { name: "Content-Type", value: "application/json" },
          { name: "X-Bot-ID", value: "" }
        ],
        body: JSON.stringify(
          {
            numbers: ["{{context.phone_number}}"]
          },
          null,
          2
        )
      },
      response_map: [
        { source_path: "0.exists", target_variable: "has_whatsapp" },
        { source_path: "0.jid", target_variable: "whatsapp_jid" }
      ],
      success_check: { status_codes: [200] }
    }
  },

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

/**
 * Evolution API Documentation
 *
 * These templates cover common WhatsApp operations, but Evolution API supports
 * many more endpoints. You can execute any Evolution API request by configuring
 * a custom API_ACTION node.
 *
 * Full API documentation:
 * @see https://doc.evolution-api.com/v2/en/get-started/introduction
 *
 * Postman Collection:
 * @see https://www.postman.com/agenciadgcode/evolution-api/documentation/nm0wqgt/evolution-api-v2-3
 */
export const EVOLUTION_API_DOCS_URL = "https://doc.evolution-api.com/v2/en/get-started/introduction";
export const EVOLUTION_API_POSTMAN_URL = "https://www.postman.com/agenciadgcode/evolution-api/documentation/nm0wqgt/evolution-api-v2-3";
