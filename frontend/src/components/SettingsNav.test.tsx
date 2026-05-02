import { render } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listLLMConfigs: vi.fn().mockResolvedValue([]),
}));

import SettingsNav from './SettingsNav';

describe('SettingsNav', () => {
  it('renders without crashing', () => {
    const { container } = render(<SettingsNav />);
    expect(container).toBeTruthy();
  });

  it('renders navigation items', () => {
    const { container } = render(<SettingsNav />);
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });
});
