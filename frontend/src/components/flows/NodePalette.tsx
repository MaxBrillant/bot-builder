import {
  MessageSquare,
  List,
  Globe,
  GitBranch,
  MessageCircle,
  Braces,
} from "lucide-react";

interface NodeTypeItem {
  type: string;
  label: string;
  icon: React.ElementType;
  description: string;
  color: string;
}

const nodeTypes: NodeTypeItem[] = [
  {
    type: "PROMPT",
    label: "Prompt",
    icon: MessageSquare,
    description: "Collect user input",
    color: "text-node-prompt",
  },
  {
    type: "MENU",
    label: "Menu",
    icon: List,
    description: "Present options",
    color: "text-node-menu",
  },
  {
    type: "API_ACTION",
    label: "API Action",
    icon: Globe,
    description: "Call external API",
    color: "text-node-api",
  },
  {
    type: "LOGIC_EXPRESSION",
    label: "Logic",
    icon: GitBranch,
    description: "Conditional routing",
    color: "text-node-logic",
  },
  {
    type: "TEXT",
    label: "Text",
    icon: MessageCircle,
    description: "Display text",
    color: "text-node-text",
  },
  {
    type: "SET_VARIABLE",
    label: "Set Variable",
    icon: Braces,
    description: "Assign variable values",
    color: "text-node-setvariable",
  },
];

export default function NodePalette() {
  const onDragStart = (event: React.DragEvent, nodeType: string) => {
    event.dataTransfer.setData("application/reactflow", nodeType);
    event.dataTransfer.effectAllowed = "move";
  };

  return (
    <div className="w-[200px] bg-background border-r overflow-y-auto">
      <div className="p-4">
        <h2 className="font-semibold text-sm text-foreground mb-4">Node Types</h2>
        <div className="space-y-2">
          {nodeTypes.map((node) => {
            const Icon = node.icon;
            return (
              <div
                key={node.type}
                draggable
                onDragStart={(e) => onDragStart(e, node.type)}
                className="p-3 border rounded-lg cursor-move hover:border-border hover:shadow-md transition-all bg-background"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Icon className={`w-4 h-4 ${node.color}`} />
                  <span className="font-medium text-sm">{node.label}</span>
                </div>
                <p className="text-xs text-muted-foreground">{node.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
