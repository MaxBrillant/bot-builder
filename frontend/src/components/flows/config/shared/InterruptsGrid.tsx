import { ListEditor, type FieldDefinition } from "./list-editor";
import type { Interrupt } from "@/lib/types";
import { SystemConstraints } from "@/lib/types";

interface InterruptsGridProps {
  value: Interrupt[];
  onChange: (value: Interrupt[]) => void;
  availableNodes: Array<{ id: string; name: string }>;
  errors: Record<string, string>;
}

export function InterruptsGrid({
  value,
  onChange,
  availableNodes,
  errors = {},
}: InterruptsGridProps) {
  const safeAvailableNodes = availableNodes ?? [];

  const fields: FieldDefinition<Interrupt>[] = [
    {
      key: "input",
      label: "Keyword",
      type: "input",
      placeholder: "e.g., cancel, back, help",
      maxLength: SystemConstraints.MAX_INTERRUPT_KEYWORD_LENGTH,
    },
    {
      key: "target_node",
      label: "Jump To Node",
      type: "select",
      placeholder: "Select node",
      options: safeAvailableNodes
        .sort((a, b) => a.name.localeCompare(b.name))
        .map((node) => ({ value: node.id, label: node.name })),
    },
  ];

  return (
    <ListEditor
      items={value}
      onChange={onChange}
      fields={fields}
      createEmpty={() => ({ input: "", target_node: "" })}
      renderColumns={(interrupt) => {
        const nodeName = safeAvailableNodes.find(
          (n) => n.id === interrupt.target_node
        )?.name;
        return [
          <span key="keyword" className="font-mono text-xs">
            {interrupt.input || <span className="text-muted-foreground">keyword</span>}
          </span>,
          <span key="node" className="text-xs">
            {nodeName || <span className="text-muted-foreground">node</span>}
          </span>,
        ];
      }}
      listHeaders={["Keyword", "Node"]}
      addLabel="Add Escape Key"
      errorPrefix="interrupts"
      errors={errors}
      helpText="Special words that let users jump to a different part of the conversation"
      helpTooltip={
        <>
          <p className="mb-2">
            If a user types one of these keywords at any time, they'll immediately jump to the node you choose. This lets users exit, go back, or get help without completing the current step.
          </p>
          <p className="text-xs font-medium mt-2">Common uses:</p>
          <ul className="list-none space-y-1 mt-1 text-xs">
            <li>
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">cancel</code> - Let users exit to main menu
            </li>
            <li>
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">back</code> - Return to a previous step
            </li>
            <li>
              <code className="bg-primary-foreground text-primary px-1 py-0.5 rounded">help</code> - Jump to help information
            </li>
          </ul>
          <p className="mt-2 text-xs">
            Matching ignores capitalization (CANCEL = cancel = Cancel).
          </p>
        </>
      }
      editorSide="left"
    />
  );
}
