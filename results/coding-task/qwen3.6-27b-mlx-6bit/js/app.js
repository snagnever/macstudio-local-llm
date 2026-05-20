let currentFilter = 'all';
let searchQuery = '';

function getFilteredTasks() {
  let tasks = loadTasks();

  if (currentFilter === 'active') {
    tasks = tasks.filter(t => !t.completed);
  } else if (currentFilter === 'completed') {
    tasks = tasks.filter(t => t.completed);
  }

  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    tasks = tasks.filter(t => t.text.toLowerCase().includes(q));
  }

  return tasks;
}

function refresh() {
  renderTasks(getFilteredTasks());
}

document.getElementById('add-btn').addEventListener('click', addNewTask);

document.getElementById('task-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') addNewTask();
});

function addNewTask() {
  const input = document.getElementById('task-input');
  const text = input.value.trim();
  if (!text) return;
  addTask(text);
  input.value = '';
  refresh();
}

document.getElementById('task-list').addEventListener('click', (e) => {
  const item = e.target.closest('.task-item');
  if (!item) return;

  const id = item.dataset.id;

  if (e.target.closest('.task-checkbox')) {
    toggleTask(id);
    refresh();
  } else if (e.target.closest('.task-delete')) {
    deleteTask(id);
    refresh();
  }
});

document.getElementById('task-list').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    const checkbox = e.target.closest('.task-checkbox');
    if (checkbox) {
      e.preventDefault();
      const id = checkbox.closest('.task-item').dataset.id;
      toggleTask(id);
      refresh();
    }
  }
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentFilter = btn.dataset.filter;
    refresh();
  });
});

document.getElementById('search-input').addEventListener('input', (e) => {
  searchQuery = e.target.value.trim();
  refresh();
});

document.getElementById('clear-completed').addEventListener('click', () => {
  clearCompleted();
  refresh();
});

refresh();
