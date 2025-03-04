# Глобальные переменные для хранения текущей сортировки
current_sort_field = (
    "memory"  # Возможные значения: "name", "memory", "cpu", "pid", "status"
)
current_sort_order = True  # False – по возрастанию, True – по убыванию
selected_pids: list[int] = []  # Список для хранения PID выделенных процессов
processes_sorted: list[int] = []
filtered_processes: list[int] = []
is_search_active = False
search_term = ""  # Переменная для хранения строки поиска
is_updating = False
