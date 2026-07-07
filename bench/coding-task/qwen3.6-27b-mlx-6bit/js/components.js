function createTaskElement(task) {
  const li = document.createElement('li');
  li.className = 'task-item' + (task.completed ? ' completed' : '');
  li.dataset.id = task.id;

  const checkbox = document.createElement('div');
  checkbox.className = 'task-checkbox';
  checkbox.setAttribute('role', 'checkbox');
  checkbox.setAttribute('aria-checked', task.completed);
  checkbox.setAttribute('tabindex', '0');

  const text = document.createElement('span');
  text.className = 'task-text';
  text.textContent = task.text;

  const delBtn = document.createElement('button');
  delBtn.className = 'task-delete';
  delBtn.innerHTML = '&times;';
  delBtn.setAttribute('aria-label', 'Delete task');

  li.appendChild(checkbox);
  li.appendChild(text);
  li.appendChild(delBtn);

  return li;
}

function renderTasks(tasks) {
  const list = document.getElementById('task-list');
  list.innerHTML = '';

  if (tasks.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.innerHTML = '<div class="icon">✓</div><p>No tasks yet. Add one above!</p>';
    list.appendChild(empty);
  } else {
    tasks.forEach(task => {
      list.appendChild(createTaskElement(task));
    });
  }

  updateCount(tasks);
}

function updateCount(tasks) {
  const count = document.getElementById('task-count');
  const active = tasks.filter(t => !t.completed).length;
  count.textContent = active + ' task' + (active !== 1 ? 's' : '') + ' remaining';
}
