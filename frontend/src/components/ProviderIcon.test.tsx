import { render } from '@testing-library/react';

import { ProviderIcon } from './ProviderIcon';

describe('ProviderIcon', () => {
  it('renders an SVG for known provider', () => {
    const { container } = render(<ProviderIcon provider="deepseek" />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('renders fallback for unknown provider', () => {
    const { container } = render(<ProviderIcon provider="unknown-provider" />);
    // Should render something (either icon or fallback)
    expect(container.innerHTML.length).toBeGreaterThan(0);
  });
});
