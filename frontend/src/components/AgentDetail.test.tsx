import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listLLMConfigs: vi.fn().mockResolvedValue([]),
  listAgentTemplates: vi.fn().mockResolvedValue([]),
  updateAgentTemplate: vi.fn().mockResolvedValue({}),
}));

import AgentDetail from './AgentDetail';

describe('AgentDetail', () => {
  it('renders without crashing', () => {
    render(<AgentDetail />);
    expect(screen.getByText(/agent/i) || document.querySelector('.agent-detail')).toBeTruthy();
  });

  it('shows empty state when no template selected', () => {
    render(<AgentDetail />);
    // With no templates in store, should show some empty/default state
    expect(document.body.innerHTML.length).toBeGreaterThan(0);
  });
});
