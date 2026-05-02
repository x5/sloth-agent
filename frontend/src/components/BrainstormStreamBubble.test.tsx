import { render, screen } from '@testing-library/react';

import BrainstormStreamBubble from './BrainstormStreamBubble';

describe('BrainstormStreamBubble', () => {
  it('renders agent name', () => {
    render(<BrainstormStreamBubble agentName="TestAgent" />);
    expect(screen.getByText('TestAgent')).toBeInTheDocument();
  });

  it('renders streaming content when provided', () => {
    render(
      <BrainstormStreamBubble agentName="Agent" streamingContent="Hello world" />,
    );
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('renders without content when streamingContent is empty', () => {
    const { container } = render(
      <BrainstormStreamBubble agentName="Agent" streamingContent="" />,
    );
    expect(container.querySelector('.chat-message')).toBeInTheDocument();
  });

  it('displays agent number when provided', () => {
    render(<BrainstormStreamBubble agentName="Agent" agentNumber={3} />);
    expect(screen.getByText('3')).toBeInTheDocument();
  });
});
