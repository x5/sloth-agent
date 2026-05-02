import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listTeamAgents: vi.fn().mockResolvedValue([]),
  listAgentTemplates: vi.fn().mockResolvedValue([]),
  listBrainstormSessions: vi.fn().mockResolvedValue([]),
  listLLMConfigs: vi.fn().mockResolvedValue([]),
}));

import RightPanel from './RightPanel';

describe('RightPanel', () => {
  it('renders without crashing', () => {
    const { container } = render(<RightPanel />);
    expect(container).toBeTruthy();
  });

  it('renders panel content', () => {
    const { container } = render(<RightPanel />);
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });
});
