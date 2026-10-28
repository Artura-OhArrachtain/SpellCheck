const input = document.querySelector('#text');
const grammar = document.querySelector('#grammar');
const button = document.querySelector('#check');
const status = document.querySelector('#status');
const results = document.querySelector('#results');

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
    const response = await fetch('http://127.0.0.1:8000/check', {
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
    status.textContent = 'Could not reach Spellcheck. Start the Linux app or run spellcheck-server first.';
  } finally {
    button.disabled = false;
  }
});
