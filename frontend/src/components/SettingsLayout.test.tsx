import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('../api/client', () => ({
  listLLMConfigs: vi.fn().mockResolvedValue([]),
}));

import SettingsLayout from './SettingsLayout';

describe('SettingsLayout', () => {
  it('renders the settings title', () => {
    render(<SettingsLayout />);
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('renders without crashing', () => {
    const { container } = render(<SettingsLayout />);
    expect(container.querySelector('.settings-layout')).toBeInTheDocument();
  });
});
