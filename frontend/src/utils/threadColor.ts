/**
 * Thread color utilities for brainstorm reply chains.
 *
 * Each root message gets a stable hue derived from its ID.
 * Reply descendants share the same color as their root.
 */

import type { Message } from "../api/client";

/** Traverse parent_message_id links to find the root message ID. */
export function getRootId(id: string, messages: Pick<Message, "id" | "parent_message_id">[]): string {
  const map = new Map(messages.map((m) => [m.id, m.parent_message_id]));
  let current = id;
  const visited = new Set<string>();
  while (true) {
    const parent = map.get(current);
    if (!parent || visited.has(current)) return current;
    visited.add(current);
    current = parent;
  }
}

/** Derive a stable hue (0-359) from a message ID string. */
export function threadHue(rootId: string): number {
  let hash = 0;
  for (let i = 0; i < rootId.length; i++) {
    hash = (hash * 31 + rootId.charCodeAt(i)) >>> 0;
  }
  return hash % 360;
}

/** Return an HSL color string for a thread, given its root message ID. */
export function threadColor(rootId: string): string {
  return `hsl(${threadHue(rootId)}, 45%, 58%)`;
}
