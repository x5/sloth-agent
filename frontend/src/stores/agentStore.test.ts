import { beforeEach, afterEach, describe, expect, it, vi } from "vitest";

const { listTeamAgentsMock } = vi.hoisted(() => ({
  listTeamAgentsMock: vi.fn(),
}));

vi.mock("../api/client", () => ({
  listTeamAgents: listTeamAgentsMock,
  listAgentTemplates: vi.fn(),
  addAgentToTeam: vi.fn(),
  updateTeamAgent: vi.fn(),
  removeAgentFromTeam: vi.fn(),
}));

function makeTeamAgent(id: string, status: "idle" | "working" = "idle") {
  return {
    id,
    inspiration_id: "insp-1",
    template_id: null,
    name: `Agent ${id}`,
    role: "lead",
    model: "gpt-4o-mini",
    status,
    joined_at: new Date().toISOString(),
  };
}

describe("agentStore status sync", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.useFakeTimers();
    listTeamAgentsMock.mockReset();
    listTeamAgentsMock.mockResolvedValue([makeTeamAgent("a", "working")]);
  });

  afterEach(() => {
    vi.runOnlyPendingTimers();
    vi.useRealTimers();
  });

  it("dedupes startStatusSync for same inspiration", async () => {
    const { useAgentStore } = await import("./agentStore");
    useAgentStore.setState({ teamMembers: [makeTeamAgent("a", "idle")] });

    await useAgentStore.getState().startStatusSync("insp-1");
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(0);
    expect(useAgentStore.getState().teamMembers[0]?.status).toBe("working");

    await useAgentStore.getState().startStatusSync("insp-1");
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(0);

    await vi.advanceTimersByTimeAsync(400);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1200);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(2);

    await useAgentStore.getState().stopStatusSync();
    await vi.advanceTimersByTimeAsync(1200);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(3);

    await useAgentStore.getState().stopStatusSync();
    await vi.advanceTimersByTimeAsync(249);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(3);

    await vi.advanceTimersByTimeAsync(1);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(4);
  });

  it("stops interval and performs one trailing refresh on stop", async () => {
    const { useAgentStore } = await import("./agentStore");
    useAgentStore.setState({ teamMembers: [makeTeamAgent("a", "idle")] });

    await useAgentStore.getState().startStatusSync("insp-1");
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(0);

    await vi.advanceTimersByTimeAsync(400);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(1200);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(2);

    await useAgentStore.getState().stopStatusSync();

    await vi.advanceTimersByTimeAsync(250);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(3);

    await vi.advanceTimersByTimeAsync(2400);
    expect(listTeamAgentsMock).toHaveBeenCalledTimes(3);
  });
});
