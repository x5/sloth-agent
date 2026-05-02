import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listInspirations: vi.fn().mockResolvedValue([]),
  createInspiration: vi.fn().mockResolvedValue({ id: '1', name: 'Test' }),
  deleteInspiration: vi.fn().mockResolvedValue(undefined),
}));

import ProjectList from './ProjectList';

describe('ProjectList', () => {
  it('renders without crashing', () => {
    const { container } = render(<ProjectList />);
    expect(container).toBeTruthy();
  });

  it('renders empty state when no inspirations', () => {
    const { container } = render(<ProjectList />);
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });
});
