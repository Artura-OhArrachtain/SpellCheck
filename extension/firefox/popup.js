const input = document.querySelector('#text');
const apiUrl = document.querySelector('#api-url');
const grammar = document.querySelector('#grammar');
const button = document.querySelector('#check');
const status = document.querySelector('#status');
const results = document.querySelector('#results');

browser.storage.local.get('apiUrl').then(saved => {
  if (saved.apiUrl) apiUrl.value = saved.apiUrl;
});

apiUrl.addEventListener('change', () => {
  browser.storage.local.set({ apiUrl: apiUrl.value.trim() });
});

function addGroup(title, items, format) {
  const heading = document.createElement('h2');
  heading.textContent = title + ' (' + items.length + ')';
  results.append(heading);
  if (!items.length) {
    const empty = document.createElement('p');
    empty.textContent = 'No issues found.';
    results.append(empty);
  }
  items.forEach(item => {
    const row = document.createElement('div');
    row.className = 'issue';
    const content = format(item);
    const titleNode = document.createElement('strong');
    titleNode.textContent = content.title;
    row.append(titleNode);
    const detail = document.createElement('span');
    detail.textContent = content.detail;
    row.append(detail);
    results.append(row);
  });
}

button.addEventListener('click', async () => {
  const text = input.value;
  if (!text.trim()) {
    status.textContent = 'Enter some text to check.';
    return;
  }

  button.disabled = true;
  status.textContent = 'Checking…';
  results.replaceChildren();
  try {
    const server = new URL(apiUrl.value.trim());
    if (server.protocol !== 'http:' && server.protocol !== 'https:') {
      throw new Error('Use an HTTP or HTTPS Spellcheck server URL.');
    }
    const permission = server.origin + '/*';
    const hasPermission = await browser.permissions.contains({ origins: [permission] });
    if (!hasPermission && !(await browser.permissions.request({ origins: [permission] }))) {
      throw new Error('Firefox needs permission to reach that Spellcheck server.');
    }

    const response = await fetch(new URL('/check', server.origin), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, grammar: grammar.checked })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The check failed.');
    if (data.warning) {
      const warning = document.createElement('p');
      warning.className = 'warning';
      warning.textContent = data.warning;
      results.append(warning);
    }
    addGroup('Spelling', data.spelling, item => ({
      title: item.word + ' (position ' + item.position + ')',
      detail: 'Suggestions: ' + (item.suggestions.join(', ') || 'none')
    }));
    if (grammar.checked) {
      addGroup('Grammar and style', data.grammar, item => ({
        title: item.issue_type + ' (position ' + item.offset + ')',
        detail: item.message + (item.replacements.length ? ' Suggestions: ' + item.replacements.join(', ') : '')
      }));
    }
    status.textContent = 'Check complete.';
  } catch (error) {
    status.textContent = error.message || 'Could not reach the Spellcheck server.';
  } finally {
    button.disabled = false;
  }
});
