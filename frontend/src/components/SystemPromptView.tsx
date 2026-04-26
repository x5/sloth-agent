interface Section {
  number: string;
  title: string;
  body: string;
}

function parseSections(text: string): Section[] {
  const sections: Section[] = [];
  const parts = text.split(/^## /gm);

  for (const part of parts) {
    const trimmed = part.trim();
    if (!trimmed) continue;

    const headerEnd = trimmed.indexOf("\n");
    const headerLine = headerEnd === -1 ? trimmed : trimmed.slice(0, headerEnd);
    const body = headerEnd === -1 ? "" : trimmed.slice(headerEnd + 1).trim();

    const headerMatch = headerLine.match(/^(\d+)\.\s*(.+)/);
    if (headerMatch) {
      sections.push({
        number: headerMatch[1],
        title: headerMatch[2],
        body,
      });
    } else {
      // Content before the first ## header — treat as preamble
      if (sections.length === 0) {
        sections.push({ number: "", title: "", body: trimmed });
      }
    }
  }

  return sections;
}

export default function SystemPromptView({ text }: { text: string }) {
  const sections = parseSections(text);

  if (sections.length === 0) {
    return (
      <span className="detail-field__value" style={{ color: "var(--text-muted)" }}>
        No system prompt configured
      </span>
    );
  }

  return (
    <div className="sp-sections">
      {sections.map((sec, i) => (
        <div key={i} className="sp-section">
          {sec.title && (
            <div className="sp-section__header">
              <span className="sp-section__number">{sec.number}</span>
              <span className="sp-section__title">{sec.title}</span>
            </div>
          )}
          <div className="sp-section__body">{sec.body}</div>
        </div>
      ))}
    </div>
  );
}
