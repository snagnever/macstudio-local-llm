const STORAGE_KEY = 'taskmanager_tasks';

function loadTasks() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

function saveTasks(tasks) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
}

function addTask(text) {
  const tasks = loadTasks();
  tasks.unshift({
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 7),
    text: text.trim(),
    completed: false,
    createdAt: Date.now()
  });
  saveTasks(tasks);
}

function toggleTask(id) {
  const tasks = loadTasks();
  const task = tasks.find(t => t.id === id);
  if (task) {
    task.completed = !task.completed;
  }
  saveTasks(tasks);
}

function deleteTask(id) {
  const tasks = loadTasks().filter(t => t.id !== id);
  saveTasks(tasks);
}

function clearCompleted() {
  const tasks = loadTasks().filter(t => !t.completed);
  saveTasks(tasks);
}
