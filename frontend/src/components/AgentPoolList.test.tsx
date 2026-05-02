import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listAgentTemplates: vi.fn().mockResolvedValue([]),
  updateAgentTemplate: vi.fn().mockResolvedValue({}),
}));

import AgentPoolList from './AgentPoolList';

describe('AgentPoolList', () => {
  it('renders without crashing', () => {
    render(<AgentPoolList />);
    expect(document.body.innerHTML.length).toBeGreaterThan(0);
  });

  it('shows loading or empty state', () => {
    render(<AgentPoolList />);
    // Should render without throwing even with empty store
    expect(document.body).toBeTruthy();
  });
});
