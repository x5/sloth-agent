import { fireEvent, render, screen } from '@testing-library/react';

import ConfirmModal from './ConfirmModal';

describe('ConfirmModal', () => {
  it('renders title, message, and custom confirm label when open', () => {
    render(
      <ConfirmModal
        open
        title="Delete Project"
        message="This action cannot be undone"
        confirmLabel="Confirm Delete"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    expect(screen.getByText('Delete Project')).toBeInTheDocument();
    expect(screen.getByText('This action cannot be undone')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Confirm Delete' })).toBeInTheDocument();
  });

  it('calls callbacks for confirm and cancel interactions', () => {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();

    const { container } = render(
      <ConfirmModal
        open
        title="Delete Agent"
        message="Are you sure?"
        onConfirm={onConfirm}
        onCancel={onCancel}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    fireEvent.click(container.querySelector('.modal-overlay')!);

    expect(onConfirm).toHaveBeenCalledTimes(1);
    expect(onCancel).toHaveBeenCalledTimes(2);
  });

  it('does not render when closed', () => {
    render(
      <ConfirmModal
        open={false}
        title="Delete"
        message="Message"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    expect(screen.queryByText('Delete')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancel' })).not.toBeInTheDocument();
  });
});
