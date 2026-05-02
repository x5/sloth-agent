import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listLLMConfigs: vi.fn().mockResolvedValue([]),
}));

import ProviderList from './ProviderList';

describe('ProviderList', () => {
  it('renders without crashing', () => {
    const { container } = render(<ProviderList />);
    expect(container).toBeTruthy();
  });

  it('renders empty state when no providers', () => {
    const { container } = render(<ProviderList />);
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });
});
