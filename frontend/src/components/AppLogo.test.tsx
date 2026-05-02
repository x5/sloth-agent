import { render } from '@testing-library/react';

import AppLogo from './AppLogo';

describe('AppLogo', () => {
  it('renders the logo SVG', () => {
    const { container } = render(<AppLogo />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
  });

  it('has a title attribute', () => {
    const { container } = render(<AppLogo />);
    const logo = container.querySelector('.app-logo');
    expect(logo).toHaveAttribute('title');
  });
});
