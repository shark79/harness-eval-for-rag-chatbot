export async function request(path, body) {
  const response = await fetch(path, body === undefined ? {} : {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  let result;
  try { result = await response.json(); }
  catch { throw new Error('The server returned an unreadable response. Try again.'); }
  if (!response.ok) throw new Error(typeof result.error === 'string' ? result.error : `Request failed (${response.status}).`);
  return result;
}
