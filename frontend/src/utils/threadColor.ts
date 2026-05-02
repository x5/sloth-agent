/**
 * Thread color utilities for brainstorm reply chains.
 *
 * Each root message gets a stable hue derived from its ID.
 * Reply descendants share the same color as their root.
 */

import type { Message } from "../api/client";

/** Traverse parent_message_id links to find the root message ID.
 *
 * The visited Set detects cycles (returns current node if already seen).
 * maxDepth is an extra safety cap against unexpectedly deep chains.
 */
export function getRootId(
  id: string,
  messages: Pick<Message, "id" | "parent_message_id">[],
  maxDepth = 50,
): string {
  const map = new Map(messages.map((m) => [m.id, m.parent_message_id]));
  let current = id;
  const visited = new Set<string>();
  while (maxDepth-- > 0) {
    const parent = map.get(current);
    if (!parent || visited.has(current)) return current;
    visited.add(current);
    current = parent;
  }
  return current;
}

/** Derive a stable hue (0-359) from a message ID string using FNV-1a for uniform distribution. */
export function threadHue(rootId: string): number {
  let hash = 2166136261; // FNV offset basis (32-bit)
  for (let i = 0; i < rootId.length; i++) {
    hash ^= rootId.charCodeAt(i);
    hash = (hash * 16777619) >>> 0; // FNV prime, keep 32-bit unsigned
  }
  return hash % 360;
}

/** Return an HSL color string for a thread, given its root message ID. */
export function threadColor(rootId: string): string {
  return `hsl(${threadHue(rootId)}, 45%, 58%)`;
}
