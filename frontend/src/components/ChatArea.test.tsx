import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { getMessagesMock, streamChatMessageMock } = vi.hoisted(() => ({
  getMessagesMock: vi.fn(),
  streamChatMessageMock: vi.fn(),
}));

let inspirationState: Record<string, unknown>;
let uiState: Record<string, unknown>;
let agentState: Record<string, unknown>;
let brainstormState: Record<string, unknown>;

vi.mock("../api/client", () => ({
  getMessages: getMessagesMock,
  streamChatMessage: streamChatMessageMock,
}));

vi.mock("../stores/inspirationStore", () => ({
  useInspirationStore: (selector: (s: Record<string, unknown>) => unknown) => selector(inspirationState),
}));

vi.mock("../stores/uiStore", () => ({
  useUIStore: (selector: (s: Record<string, unknown>) => unknown) => selector(uiState),
}));

vi.mock("../stores/agentStore", () => ({
  useAgentStore: (selector: (s: Record<string, unknown>) => unknown) => selector(agentState),
}));

vi.mock("../stores/brainstormStore", () => ({
  useBrainstormStore: (selector: (s: Record<string, unknown>) => unknown) => selector(brainstormState),
}));

import ChatArea from "./ChatArea";

describe("ChatArea divider rendering", () => {
  beforeEach(() => {
    getMessagesMock.mockReset();
    streamChatMessageMock.mockReset();

    inspirationState = {
      inspirations: [{ id: "insp-1", name: "Demo" }],
      activeId: "insp-1",
    };
    uiState = {
      col4Content: "none",
      openCol4: vi.fn(),
    };
    agentState = {
      teamMembers: [],
      fetchTeam: vi.fn(),
      startStatusSync: vi.fn(),
      stopStatusSync: vi.fn(),
    };
    brainstormState = {
      sessions: [],
      fetchAll: vi.fn(),
      brainstormMode: false,
      activeId: null,
      startBrainstorm: vi.fn(),
      stopBrainstorm: vi.fn(),
      startDiscussion: vi.fn(),
      stopDiscussion: vi.fn(),
      connectSession: vi.fn(),
      disconnectSession: vi.fn(),
      injectMessage: vi.fn(),
      setReplyingTo: vi.fn(),
      discussionActive: false,
      discussionConnected: false,
      activeAgentId: null,
      activeAgentName: null,
      activeAgentNumber: null,
      activeParentMessageId: null,
      discussionMessages: [],
      streamingContent: "",
      replyingToId: null,
      replyingToContent: null,
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders persisted system divider label", async () => {
    brainstormState.sessions = [{ id: "sess-1" }];
    getMessagesMock.mockResolvedValue([
      {
        id: "m1",
        inspiration_id: "insp-1",
        agent_id: null,
        role: "system",
        content: "Brainstorm #1 Started",
        created_at: "2026-05-02T00:00:00.000Z",
        agent_name: null,
        agent_number: null,
        agent_model: null,
        mode: "brainstorm",
        brainstorm_session_id: "sess-1",
        parent_message_id: null,
        round: 1,
        intent: "divider_start",
        truncated: false,
      },
    ]);

    render(<ChatArea />);

    expect(await screen.findByText("Brainstorm #1 Started")).toBeTruthy();
  });

  it("renders synthetic ended divider when system divider messages are missing", async () => {
    brainstormState.sessions = [
      {
        id: "sess-2",
        created_at: "2026-05-02T00:00:00.000Z",
        ended_at: "2026-05-02T00:10:00.000Z",
      },
    ];
    getMessagesMock.mockResolvedValue([]);

    render(<ChatArea />);

    expect(await screen.findByText("Brainstorm #1 Ended")).toBeTruthy();
  });

  it("shows a clickable brainstorm interrupt icon next to the bolt while discussion is active", async () => {
    const stopDiscussion = vi.fn();
    const disconnectSession = vi.fn();
    brainstormState = {
      ...brainstormState,
      brainstormMode: true,
      discussionConnected: true,
      activeAgentId: "agent-1",
      activeAgentName: "Lead",
      stopDiscussion,
      disconnectSession,
    };
    getMessagesMock.mockResolvedValue([]);

    render(<ChatArea />);

    const interruptButton = await screen.findByRole("button", { name: "Interrupt Brainstorm" });
    expect(interruptButton).toBeEnabled();
    expect(interruptButton.className).toContain("chatarea__tool-btn--active");

    fireEvent.click(interruptButton);

    expect(stopDiscussion).toHaveBeenCalledTimes(1);
    expect(disconnectSession).not.toHaveBeenCalled();
    expect(interruptButton).toBeDisabled();
    expect(interruptButton.className).toContain("chatarea__tool-btn--muted");
  });

  it("keeps the brainstorm interrupt icon visible but gray when connected but no agent is replying", async () => {
    brainstormState = {
      ...brainstormState,
      brainstormMode: true,
      discussionConnected: true,
      discussionActive: true,
      activeAgentId: null,
    };
    getMessagesMock.mockResolvedValue([]);

    render(<ChatArea />);

    const interruptButton = await screen.findByRole("button", { name: "Interrupt Brainstorm" });
    expect(interruptButton).toBeDisabled();
    expect(interruptButton.className).toContain("chatarea__tool-btn--muted");
  });
});
