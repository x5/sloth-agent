import { render, screen } from '@testing-library/react';

import SystemPromptView from './SystemPromptView';

describe('SystemPromptView', () => {
  it('renders preamble text before sections', () => {
    render(<SystemPromptView text="Hello world" />);
    expect(screen.getByText('Hello world')).toBeInTheDocument();
  });

  it('renders numbered sections with headers', () => {
    const text = `## 1. Test Section
Some body text`;
    render(<SystemPromptView text={text} />);
    expect(screen.getByText('Test Section')).toBeInTheDocument();
    expect(screen.getByText('Some body text')).toBeInTheDocument();
  });

  it('renders empty state when text is empty', () => {
    render(<SystemPromptView text="" />);
    expect(screen.getByText('No system prompt configured')).toBeInTheDocument();
  });

  it('renders multiple sections', () => {
    const text = `## 1. First
Body one
## 2. Second
Body two`;
    render(<SystemPromptView text={text} />);
    expect(screen.getByText('First')).toBeInTheDocument();
    expect(screen.getByText('Second')).toBeInTheDocument();
  });
});
