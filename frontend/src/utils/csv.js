export function serializeResponses(rows) {
  const quote = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  return 'ticket_text,assistant_answer,category\r\n' + rows.map(row =>
    [row.ticket_text, row.assistant_answer ?? row.answer, row.category].map(quote).join(',') + '\r\n'
  ).join('');
}
