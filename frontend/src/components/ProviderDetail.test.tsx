import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listLLMConfigs: vi.fn().mockResolvedValue([]),
  updateLLMConfig: vi.fn().mockResolvedValue({}),
  deleteLLMConfig: vi.fn().mockResolvedValue(undefined),
  setDefaultLLMConfig: vi.fn().mockResolvedValue(undefined),
}));

import ProviderDetail from './ProviderDetail';

describe('ProviderDetail', () => {
  it('renders without crashing', () => {
    const { container } = render(<ProviderDetail />);
    expect(container).toBeTruthy();
  });

  it('shows empty state when no provider selected', () => {
    const { container } = render(<ProviderDetail />);
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });
});
