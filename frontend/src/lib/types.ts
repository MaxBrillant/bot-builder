// User types
export interface User {
  user_id: string;
  email: string;
  oauth_provider?: string;
  oauth_id?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Bot types
export interface Bot {
  bot_id: string;
  owner_user_id: string;
  name: string;
  description?: string;
  webhook_url: string;
  webhook_secret?: string;
  status: "ACTIVE" | "INACTIVE";
  created_at: string;
  updated_at: string;
  flow_count?: number; // Backend returns this when eager loading flows
  // WhatsApp connection info
  whatsapp_connected: boolean;
  whatsapp_phone_number?: string;
  whatsapp_status?: "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";
}

// Bot list response from backend
export interface BotListResponse {
  bots: Bot[];
  total: number;
}

// WhatsApp Status Response
export interface WhatsAppStatus {
  status: "DISCONNECTED" | "CONNECTING" | "CONNECTED" | "ERROR";
  instance_name?: string;
  phone_number?: string;
  connected_at?: string;
  qr_code?: string; // Base64-encoded QR code (only when status=CONNECTING)
  message?: string;
}

// ============================================
// ERROR TYPES
// ============================================

// Structured error response from backend
export interface APIError {
  detail: string | APIValidationError[];
  error_code?: string;
  errors?: Array<{ type?: string; location?: string; message?: string }>;
  error?: string;
}

export interface APIValidationError {
  type: string;
  loc: (string | number)[];
  msg: string;
  input?: any;
}

// ============================================
// NODE CONFIGURATION TYPES
// ============================================

// Node types
export type NodeType =
  | "PROMPT"
  | "MENU"
  | "API_ACTION"
  | "LOGIC_EXPRESSION"
  | "MESSAGE"
  | "END";

export type ValidationType = "REGEX" | "EXPRESSION";
export type MenuSourceType = "STATIC" | "DYNAMIC";
export type HTTPMethod = "GET" | "POST" | "PUT" | "DELETE" | "PATCH";

// ============================================
// VALIDATION TYPES
// ============================================

export interface ValidationRule {
  type: ValidationType;
  rule: string;
  error_message: string;
}

// ============================================
// INTERRUPT TYPES
// ============================================

export interface Interrupt {
  input: string;
  target_node: string;
}

// ============================================
// NODE CONFIGURATION TYPES
// ============================================

// MESSAGE Node Configuration
export interface MessageNodeConfig {
  type: "MESSAGE";
  text: string; // Required, max 1024 chars
}

// PROMPT Node Configuration
export interface PromptNodeConfig {
  type: "PROMPT";
  text: string; // Required, max 1024 chars
  save_to_variable: string; // Required, max 96 chars
  validation?: ValidationRule;
  interrupts?: Interrupt[];
}

// MENU Node Configuration
export interface MenuStaticOption {
  label: string; // Required, max 96 chars
}

export interface MenuOutputMapping {
  source_path: string; // Required
  target_variable: string; // Required, max 96 chars
}

export interface MenuNodeConfig {
  type: "MENU";
  text: string; // Required, max 1024 chars
  source_type: MenuSourceType; // Required

  // STATIC source type fields
  static_options?: MenuStaticOption[]; // Required if STATIC, max 8 items

  // DYNAMIC source type fields
  source_variable?: string; // Required if DYNAMIC, max 96 chars
  item_template?: string; // Required if DYNAMIC, max 1024 chars
  output_mapping?: MenuOutputMapping[]; // Optional, only for DYNAMIC

  // Common fields
  error_message?: string; // Optional, max 512 chars
  interrupts?: Interrupt[];
}

// API_ACTION Node Configuration
export interface APIHeader {
  name: string; // Required, header name (e.g., 'Content-Type')
  value: string; // Required, header value (supports template variables)
}

export interface APIRequestConfig {
  method: HTTPMethod; // Required
  url: string; // Required, max 1024 chars, supports templates
  headers?: APIHeader[]; // Optional, array of header objects
  body?: string; // Optional, JSON string (supports template variables)
}

export interface APIResponseMapping {
  source_path: string; // Required
  target_variable: string; // Required, max 96 chars
}

export interface APISuccessCheck {
  status_codes?: number[]; // Optional, e.g., [200, 201]
  expression?: string; // Optional, max 512 chars
}

export interface APIActionNodeConfig {
  type: "API_ACTION";
  request: APIRequestConfig; // Required
  response_map?: APIResponseMapping[]; // Optional
  success_check?: APISuccessCheck; // Optional
}

// LOGIC_EXPRESSION Node Configuration
export interface LogicExpressionNodeConfig {
  type: "LOGIC_EXPRESSION";
  // Empty object - routes are configured separately
}

// END Node Configuration
export interface EndNodeConfig {
  type: "END";
  // Empty object - no configuration needed
}

// Union type for all configurations
export type NodeConfig =
  | MessageNodeConfig
  | PromptNodeConfig
  | MenuNodeConfig
  | APIActionNodeConfig
  | LogicExpressionNodeConfig
  | EndNodeConfig;

// ============================================
// VARIABLE TYPES
// ============================================

export type VariableType = "STRING" | "NUMBER" | "BOOLEAN" | "ARRAY";

// ============================================
// VALIDATION CONSTRAINT TYPES
// ============================================

export const SystemConstraints = {
  MAX_MESSAGE_LENGTH: 1024,
  MAX_ERROR_MESSAGE_LENGTH: 512,
  MAX_TEMPLATE_LENGTH: 1024,
  MAX_NODE_ID_LENGTH: 96,
  MAX_VARIABLE_NAME_LENGTH: 96,
  MAX_OPTION_LABEL_LENGTH: 96,
  MAX_STATIC_MENU_OPTIONS: 8,
  MAX_DYNAMIC_MENU_OPTIONS: 24,
  MAX_REGEX_LENGTH: 512,
  MAX_EXPRESSION_LENGTH: 512,
  MAX_REQUEST_URL_LENGTH: 1024,
  MAX_ROUTES_PER_NODE: 8,
  MAX_INTERRUPT_KEYWORD_LENGTH: 96,
  MAX_HEADERS_PER_REQUEST: 10,
  MAX_HEADER_NAME_LENGTH: 128,
  MAX_HEADER_VALUE_LENGTH: 2048,
  MAX_SOURCE_PATH_LENGTH: 256,
  MAX_STATUS_CODES_INPUT_LENGTH: 100,
  MAX_COUNTER_TEXT_LENGTH: 512,
  MAX_FLOW_NAME_LENGTH: 96,
  MAX_BOT_NAME_LENGTH: 96,
  MAX_BOT_DESCRIPTION_LENGTH: 512,
  MAX_VARIABLE_DEFAULT_LENGTH: 256,
  MAX_ROUTE_CONDITION_LENGTH: 512,
  MAX_ARRAY_LENGTH: 24,
} as const;

// ============================================
// FORM STATE TYPES
// ============================================

export interface ValidationError {
  field: string;
  message: string;
}

export interface NodeConfigFormState<T extends NodeConfig> {
  config: T;
  errors: ValidationError[];
  isDirty: boolean;
  isValid: boolean;
}

// ============================================
// FLOW TYPES
// ============================================

// Route
export interface Route {
  condition: string;
  target_node: string;
}

// Flow node
export interface FlowNode {
  id: string;
  type: NodeType;
  name: string; // Auto-generated display name (e.g., "Prompt 1", "Menu 2")
  config: NodeConfig;
  routes?: Route[];
  position: { x: number; y: number }; // Node position on canvas
}

// Flow
export interface Flow {
  flow_id?: string; // UUID from backend
  bot_id?: string; // UUID from backend
  name: string;
  trigger_keywords: string[];
  variables: Record<string, { type: VariableType; default: any }>;
  defaults?: {
    retry_logic?: {
      max_attempts: number;
      counter_text: string;
      fail_route: string;
    };
  };
  start_node_id: string;
  nodes: Record<string, FlowNode>;
  created_at?: string; // ISO timestamp
  updated_at?: string; // ISO timestamp
}

// Flow response from backend
export interface FlowResponse {
  flow_id: string;
  flow_name: string;
  bot_id: string;
  trigger_keywords: string[];
  flow_definition: {
    name: string;
    trigger_keywords: string[];
    variables: Record<string, { type: VariableType; default: any }>;
    defaults?: {
      retry_logic?: {
        max_attempts: number;
        counter_text: string;
        fail_route: string;
      };
    };
    start_node_id: string;
    nodes: Record<string, FlowNode>;
  };
  created_at: string;
  updated_at: string;
}

// Flow list response from backend
export interface FlowListResponse {
  flows: FlowResponse[];
  total: number;
  skip: number;
  limit: number;
}

// Flow creation request to backend
export interface FlowCreateRequest {
  name: string;
  trigger_keywords: string[]; // Required by backend, at least one keyword needed
  variables?: Record<string, { type: VariableType; default: any }>;
  defaults?: {
    retry_logic?: {
      max_attempts: number;
      counter_text: string;
      fail_route: string;
    };
  };
  start_node_id: string;
  nodes: Record<string, FlowNode>;
}

// Flow validation response from backend (for create/update operations)
export interface FlowValidationResponse {
  flow_id: string;
  flow_name: string;
  bot_id: string;
  status: string;
  errors: any[];
}

// ============================================
// AUTH TYPES
// ============================================

// Auth responses
// SECURITY: Token is NOT in response body - it's set via httpOnly cookie by the backend
// This prevents XSS attacks from stealing tokens via JavaScript
export interface LoginResponse {
  user: User;
}

export interface RegisterResponse extends User {
  // Backend returns just User data, not a token
  // Auto-login happens separately after registration
}

