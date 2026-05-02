import { render, fireEvent, screen } from '@testing-library/react';

import SideNavBar from './SideNavBar';

describe('SideNavBar', () => {
  it('renders without crashing', () => {
    const { container } = render(<SideNavBar />);
    expect(container.querySelector('.sidenav')).toBeInTheDocument();
  });

  it('renders navigation buttons', () => {
    render(<SideNavBar />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBeGreaterThan(0);
  });

  it('handles nav button clicks without crashing', () => {
    render(<SideNavBar />);
    const buttons = screen.getAllByRole('button');
    // Click each button to verify no crashes
    buttons.forEach((btn) => fireEvent.click(btn));
  });
});
