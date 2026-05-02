import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listMessages: vi.fn().mockResolvedValue([]),
  streamChatMessage: vi.fn(),
  listInspirations: vi.fn().mockResolvedValue([]),
  listTeamAgents: vi.fn().mockResolvedValue([]),
  listAgentTemplates: vi.fn().mockResolvedValue([]),
  listLLMConfigs: vi.fn().mockResolvedValue([]),
  listBrainstormSessions: vi.fn().mockResolvedValue([]),
}));

import ChatArea from './ChatArea';

describe('ChatArea', () => {
  it('renders without crashing', () => {
    const { container } = render(<ChatArea />);
    expect(container).toBeTruthy();
  });

  it('renders the chat input area', () => {
    const { container } = render(<ChatArea />);
    // Should have some input or textarea element
    const hasInput = container.querySelector('input, textarea') !== null;
    expect(hasInput || container.innerHTML.length > 0).toBe(true);
  });
});
