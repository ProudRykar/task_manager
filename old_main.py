import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import psutil
import pyperclip

current_sort_field = "memory"
current_sort_order = True
selected_pids = []
processes_sorted: list[int] = []
filtered_processes: list[int] = []
is_search_active = False
search_term = ""
is_updating = False

current_menu = None
global_hide_menu = None

class Context_Menu:

    def create_context_menu(self, tree, event, processes_sorted):
        """Создает контекстное меню для процесса при клике правой кнопкой мыши"""

        global current_menu
        global global_hide_menu

        def kill_process(pid):
            """Завершить процесс по PID (корректное завершение)"""

            global processes_sorted, filtered_processes
            try:
                process = psutil.Process(pid)
                process.terminate()
                messagebox.showinfo("Успех", f"Процесс {pid} завершен.")
                # Убираем процесс из результатов поиска
                filtered_processes = [proc for proc in filtered_processes if proc[0] != pid]
                update_treeview()
            except psutil.NoSuchProcess:
                messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
            except psutil.AccessDenied:
                messagebox.showerror("Ошибка", f"Нет доступа для завершения процесса {pid}.")


        def force_kill_process(pid):
            """Принудительно завершить процесс по PID (SIGKILL)"""
            global processes_sorted, filtered_processes
            try:
                process = psutil.Process(pid)
                process.kill()
                messagebox.showinfo("Успех", f"Процесс {pid} был принудительно завершен.")
                # Убираем процесс из результатов поиска
                filtered_processes = [proc for proc in filtered_processes if proc[0] != pid]
                update_treeview()
            except psutil.NoSuchProcess:
                messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
            except psutil.AccessDenied:
                messagebox.showerror("Ошибка", f"Нет доступа для завершения процесса {pid}.")
            except psutil.ZombieProcess:
                messagebox.showerror("Ошибка", f"Процесс {pid} является зомби.")

        item = tree.identify_row(event.y)
        if not item:
            return

        tree.selection_set(item)

        menu = tk.Menu(tree, tearoff=0)
        menu.config(background="#1e2120", foreground="white")
        pid = int(tree.item(item)["values"][0])

        menu.add_command(label="Завершить процесс", command=lambda: kill_process(pid))
        menu.add_command(label="Убить", command=lambda: force_kill_process(pid))

        def on_leave(event):
            global global_hide_menu

            if global_hide_menu:
                menu.after_cancel(global_hide_menu)
                global_hide_menu = None

            x, y = menu.winfo_pointerxy()

            if not (
                x >= menu.winfo_rootx()
                and x <= menu.winfo_rootx() + menu.winfo_width()
                and y >= menu.winfo_rooty()
                and y <= menu.winfo_rooty() + menu.winfo_height()
            ):

                global_hide_menu = menu.after(3000, menu.unpost)

        def on_enter(event):
            global global_hide_menu

            if global_hide_menu:
                menu.after_cancel(global_hide_menu)
                global_hide_menu = None

        def close_menu(event):
            """Закрывает контекстное меню при левом клике"""
            if current_menu:
                current_menu.unpost()

        menu.bind("<Leave>", on_leave)
        menu.bind("<Enter>", on_enter)
        tree.bind("<Button-1>", close_menu)

        if current_menu:
            current_menu.unpost()

        current_menu = menu

        menu.post(event.x_root, event.y_root)


def sort_by_memory(event=None) -> None:
    """Сортировка по памяти"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "memory":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "memory"
        current_sort_order = True
    processes_sorted.sort(
        key=lambda proc: float(proc[3].replace(" MB", "")), reverse=current_sort_order
    )
    update_treeview()


def sort_by_name(event=None) -> None:
    """Сортировка по имени"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "name":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "name"
        current_sort_order = False
    processes_sorted.sort(key=lambda proc: proc[1].lower(), reverse=current_sort_order)
    update_treeview()


def sort_by_cpu(event=None) -> None:
    """Сортировка по CPU"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "cpu":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "cpu"
        current_sort_order = True
    processes_sorted.sort(key=lambda proc: proc[2], reverse=current_sort_order)
    update_treeview()


def sort_by_pid(event=None) -> None:
    """Сортировка по PID"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "pid":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "pid"
        current_sort_order = False
    processes_sorted.sort(key=lambda proc: proc[0], reverse=current_sort_order)
    update_treeview()


def sort_by_status(event=None) -> None:
    """Сортировка по статусу"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "status":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "status"
        current_sort_order = False
    processes_sorted.sort(key=lambda proc: proc[4].lower(), reverse=current_sort_order)
    update_treeview()


def update_treeview() -> None:
    """
    Обновление отображаемых данных в Treeview.

    Обновляет данные в интерфейсе, удаляя старые строки и вставляя новые.
    Также обновляет выделенные элементы в Treeview.

    """

    global selected_pids, filtered_processes

    selected_pids = [tree.item(item)["values"][0] for item in tree.selection()]

    for row in tree.get_children():
        tree.delete(row)

    for i, proc in enumerate(filtered_processes):
        tag = "even" if i % 2 == 0 else "odd"
        item = tree.insert("", "end", values=proc, tags=(tag,))

        if proc[0] in selected_pids:
            tree.selection_add(item)


def find_processes_with_ports() -> set:
    """
    Поиск процессов с открытыми портами.

    Использует psutil для поиска всех процессов с открытыми TCP/UDP портами.

    Args:
        None

    Returns:
        (set): Множество PIDs процессов с открытыми портами.
    """

    connections = psutil.net_connections(kind="inet")
    processes_with_ports = set()

    for conn in connections:
        if conn.status == "LISTEN" and conn.pid is not None:
            pid = conn.pid
            try:
                processes_with_ports.add(pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    return processes_with_ports


def search_process(event=None) -> None:
    """
    Поиск процессов по PID, имени, порту, состоянию, зависшим процессам или вывода всех процессов с портами.

    Args:
        event (tk.Event, optional): Событие, передаваемое при активации поиска.

    Returns:
        None
    """

    global filtered_processes, is_search_active, search_term

    search_term = state_combobox.get().strip().lower()

    if search_term:
        is_search_active = True

        state_commands = {
            '/idle': 'idle',
            '/zombie': 'zombie',
            '/running': 'running',
            '/sleeping': 'sleeping',
            '/stopped': 'stopped',
            '/hanging': 'hanging'
        }

        if search_term in state_commands:
            target_state = state_commands[search_term]

            filtered_processes = [
                proc for proc in processes_sorted
                if len(proc) > 4 and proc[4].lower() == target_state
            ]

        elif search_term == "/hanging":
            hanging_processes = [
                proc for proc in processes_sorted 
                if len(proc) > 4 and is_process_hanging(proc)
            ]
            filtered_processes = hanging_processes

        elif search_term == ":ports":
            processes_with_ports = find_processes_with_ports()
            filtered_processes = [
                proc for proc in processes_sorted if proc[0] in processes_with_ports
            ]

        elif ":" in search_term and search_term != "/ports":
            port_str = search_term.lstrip(":")
            if port_str.isdigit():
                port = int(port_str)
                process_by_port = find_process_by_port(port)
                if process_by_port:
                    filtered_processes = [
                        proc for proc in processes_sorted
                        if proc[0] == process_by_port[1]
                    ]
                else:
                    filtered_processes = []
            else:
                filtered_processes = []

        else:
            if search_term.isdigit():
                filtered_processes = [
                    proc for proc in processes_sorted if str(proc[0]) == search_term
                ]
            else:
                filtered_processes = [
                    proc for proc in processes_sorted if search_term in proc[1].lower()
                ]

    else:
        is_search_active = False
        filtered_processes = processes_sorted

    update_treeview()


def is_process_hanging(proc) -> bool:
    """
    Функция для проверки, является ли процесс зависшим.

    Проверка может основываться на различных факторах, например, времени бездействия
    или других критериях.

    Args:
        proc (list): Список, представляющий процесс.

    Returns:
        bool: True, если процесс завис, иначе False.
    """
    
    try:
        last_active_time = proc[5]  
        current_time = time.time()  
        idle_threshold = 3600

        if (current_time - last_active_time) > idle_threshold:
            return True
        return False
    except IndexError:

        return False


def find_process_by_port(port) -> (tuple[str, int | None] | None):
    """
    Поиск процесса по порту.

    Args:
        port (int): Номер порта для поиска.

    Returns:
        (tuple or None): Кортеж с именем процесса и PID, если процесс найден; иначе None.
    """

    connections = psutil.net_connections(kind="inet")
    for conn in connections:
        if conn.status == "LISTEN" and conn.laddr.port == port:
            pid = conn.pid
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                return process_name, pid
            except psutil.NoSuchProcess:
                continue
    return None


def update_data() -> None:
    """
    Функция для обновления списка процессов
    Получает данные о процессах, сортирует их и обновляет отображаемые процессы.

    """
    global processes_sorted, filtered_processes, is_search_active

    if is_search_active:
        root.after(2000, update_data)
        return

    processes = list(
        psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"])
    )
    processes_sorted = []
    for proc in processes:
        try:
            pid = proc.info["pid"]
            name = proc.info.get("name", "N/A")
            cpu = proc.info["cpu_percent"]
            memory = (
                proc.info["memory_info"].rss / 1024 / 1024
                if proc.info["memory_info"]
                else 0
            )
            status = proc.info.get("status", "N/A")
            processes_sorted.append(
                (pid, name, f"{cpu:.2f}%", f"{memory:.2f} MB", status)
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
            continue

    if current_sort_field == "name":
        processes_sorted.sort(
            key=lambda proc: proc[1].lower(), reverse=current_sort_order
        )
    elif current_sort_field == "memory":
        processes_sorted.sort(
            key=lambda proc: float(proc[3].replace(" MB", "")),
            reverse=current_sort_order,
        )
    elif current_sort_field == "cpu":
        processes_sorted.sort(
            key=lambda proc: float(proc[2].replace("%", "")), reverse=current_sort_order
        )
    elif current_sort_field == "pid":
        processes_sorted.sort(key=lambda proc: proc[0], reverse=current_sort_order)
    elif current_sort_field == "status":
        processes_sorted.sort(
            key=lambda proc: proc[4].lower(), reverse=current_sort_order
        )

    if is_search_active and search_term:
        if search_term.isdigit():
            filtered_processes = [
                proc for proc in processes_sorted if str(proc[0]) == search_term
            ]
        else:
            filtered_processes = [
                proc for proc in processes_sorted if search_term in proc[1].lower()
            ]
    else:
        filtered_processes = processes_sorted

    update_treeview()
    root.after(2000, update_data)


def show_process_info(event) -> None:
    """
    Отображение информации о выбранном процессе.

    Args:
        event (tk.Event): Событие при активации отображения информации о процессе.

    Returns:
        None
    """

    selected_item = tree.selection()[0]
    selected_pid = tree.item(selected_item)["values"][0]

    for proc in filtered_processes:
        if proc[0] == selected_pid:
            display_process_info(proc)
            break


def save_pid_to_clipboard(proc) -> None:
    """
    Копирование PID процесса в буфер обмена.

    Args:
        proc (psutil.Process): Объект процесса, PID которого нужно скопировать.

    Returns:
        None
    """

    pid_info = proc[0]
    pyperclip.copy(pid_info)
    print("PID copied to clipboard")


def start_update_process_info() -> None:
    """Запуск обновлений информации о процессе"""
    global is_updating
    is_updating = True


def stop_update_process_info() -> None:
    """Остановка обновлений информации о процессе"""
    global is_updating
    is_updating = False


def update_process_info(proc, info_frame, labels=None) -> None:
    """
    Обновление информации о процессе.

    Args:
        proc (psutil.Process): Процесс для обновления данных.
        info_frame (tk.Frame): Фрейм для отображения информации о процессе.
        labels (list, optional): Список меток для обновления информации.

    Returns:
        None
    """
    
    if not is_updating:
        return

    try:
        process = psutil.Process(proc[0])
        cpu = process.cpu_percent(interval=0.5)

        start_time = process.create_time()
        active_time_seconds = int(psutil.time.time() - start_time)
        active_time = f"{active_time_seconds // 3600}h {active_time_seconds % 3600 // 60}m {active_time_seconds % 60}s"

        memory = process.memory_info().rss / 1024 / 1024
        status = process.status()
        port = None
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if conn.status == "LISTEN" and conn.pid == proc[0]:
                port = conn.laddr.port
                break

        if labels is None:

            title_label = tk.Label(
                info_frame,
                text="Process Information",
                font=("Arial", 16, "bold"),
                bg="#1e2120",
                fg="green",
            )
            title_label.pack(pady=10)

            info_section = tk.LabelFrame(
                info_frame,
                text="Details",
                bg="#1e2120",
                fg="green",
                font=("Arial", 12, "bold"),
                padx=20,
                pady=20,
            )
            info_section.pack(expand=True, fill="both", pady=10)

            pid_label = tk.Label(
                info_section,
                text=f"PID: {proc[0]}",
                bg="#1e2120",
                fg="white",
                font=("Arial", 10),
            )
            pid_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

            save_pid_button = tk.Button(
                info_section,
                text="Copy",
                command=lambda: save_pid_to_clipboard(proc),
                borderwidth=0,
                bg="#1e2120",
                foreground='green',
                relief="flat",
                anchor="center",          
                activebackground="#2d2f2e",
                highlightbackground="#1e2120",
                activeforeground="green",
            )
            save_pid_button.grid(row=0, column=0, padx=100)

            name_label = tk.Label(
                info_section,
                text=f"Name: {proc[1]}",
                bg="#1e2120",
                fg="white",
                font=("Arial", 10),
            )
            name_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

            cpu_label = tk.Label(
                info_section,
                text=f"CPU Usage: {cpu:.2f}%",
                bg="#1e2120",
                fg="white",
                font=("Arial", 10),
            )
            cpu_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

            memory_label = tk.Label(
                info_section,
                text=f"Memory Usage: {memory:.2f} MB",
                bg="#1e2120",
                fg="white",
                font=("Arial", 10),
            )
            memory_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)

            time_label = tk.Label(
            info_section,
            text=f"Active Time: {active_time}",
            bg="#1e2120",
            fg="white",
            font=("Arial", 10),
            )
            time_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)
            
            status_label = tk.Label(
                info_section,
                text=f"Status: {status}",
                bg="#1e2120",
                fg="white",
                font=("Arial", 10),
            )
            status_label.grid(row=5, column=0, sticky="w", padx=10, pady=5)

            if port:
                port_label = tk.Label(
                    info_section,
                    text=f"Port: {port}",
                    bg="#1e2120",
                    fg="white",
                    font=("Arial", 10),
                )
                port_label.grid(row=6, column=0, sticky="w", padx=10, pady=5)

            back_button = tk.Button(
                info_frame,
                text="Back",
                command=lambda: back_to_process_list(info_frame),
                font=("Arial", 12),
                bg="#1e2120",
                fg="green",
                activebackground="#2d2f2e",
                relief="flat",
                padx=10,
                pady=5,
            )
            back_button.pack(pady=20)

            labels = {
                "cpu": cpu_label,
                "memory": memory_label,
                "active_time": time_label,
                "status": status_label,
                "port": (port_label if port else None),
            }

        labels["cpu"].config(text=f"CPU Usage: {cpu:.2f}%")
        labels["memory"].config(text=f"Memory Usage: {memory:.2f} MB")
        labels["active_time"].config(text=f"Active Time: {active_time}")
        labels["status"].config(text=f"Status: {status}")
        if port:
            labels["port"].config(text=f"Port: {port}")

        if is_updating:
            root.after(1000, lambda: update_process_info(proc, info_frame, labels))

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        back_to_process_list(info_frame)


def display_process_info(proc) -> None:
    """
    Отображение подробной информации о процессе.

    Args:
        proc (psutil.Process): Процесс, для которого нужно отобразить информацию.

    Returns:
        None
    """

    tree_frame.pack_forget()
    start_update_process_info()
    info_frame = tk.Frame(root, bg="#1e2120")
    info_frame.pack(expand=True, fill="both", padx=20, pady=20)
    update_process_info(proc, info_frame)


def back_to_process_list(info_frame) -> None:
    """
    Возврат к списку процессов.

    Args:
        info_frame (tk.Frame): Фрейм, с которого нужно вернуться к списку.

    Returns:
        None
    """

    info_frame.pack_forget()
    stop_update_process_info()
    tree_frame.pack(expand=True, fill="both")


root = tk.Tk()
root.title("Task Manager")
root.geometry("600x600")
root.configure(background="#1e2120")

columns = ("PID", "Name", "CPU %", "Memory", "Status")
tree_frame = tk.Frame(root, bg="#1e2120")
tree_frame.pack(expand=True, fill="both")

scrollbar = tk.Scrollbar(tree_frame, orient="vertical")

tree = ttk.Treeview(
    tree_frame, columns=columns, show="headings", yscrollcommand=scrollbar.set
)
tree.pack(expand=True, fill="both", side="left")

scrollbar.config(command=tree.yview)
scrollbar.pack(side="right", fill="y")

tree.heading("PID", text="PID", anchor="center")
tree.column("PID", width=60, stretch=False, anchor="center")
tree.heading("Name", text="Name", anchor="center")
tree.column("Name", width=100)
tree.heading("CPU %", text="CPU %", anchor="center")
tree.column("CPU %", width=60, stretch=False, anchor="center")
tree.heading("Memory", text="Memory", anchor="center")
tree.column("Memory", width=150, stretch=False, anchor="center")
tree.heading("Status", text="Status", anchor="center")
tree.column("Status", width=80, stretch=False, anchor="center")

style = ttk.Style()
style.configure("Treeview.Heading", background="#1e2120", foreground="green")
style.configure(
    "Treeview", background="#1e2120", fieldbackground="#1e2120", foreground="green"
)
style.map("Treeview", background=[("selected", "#2d2f2e")])

tree.configure(style="Treeview")

scrollbar.config(bg="#2e2e2e", troughcolor="#2e2e2e", bd=1, relief="flat")

tree.heading("Name", command=sort_by_name)
tree.heading("CPU %", command=sort_by_cpu)
tree.heading("PID", command=sort_by_pid)
tree.heading("Memory", command=sort_by_memory)
tree.heading("Status", command=sort_by_status)

tree.tag_configure("even", background="#1e2120", foreground="green")
tree.tag_configure("odd", background="#1e2120", foreground="green")

tree.bind("<Double-1>", show_process_info)

def filter_combobox(event=None):
    """
    Фильтровать список команд в Combobox на основе введенного текста.
    Поддерживает поиск по любому тексту (цифры, команды, имена).
    """
    search_text = state_combobox.get().lower()
    
    filtered_commands = [command for command in state_commands if search_text in command.lower()]
    
    current_value = state_combobox.get()

    state_combobox['values'] = filtered_commands
    
    if not filtered_commands or current_value not in filtered_commands:
        state_combobox.set(current_value)

def show_dropdown(event=None):
    """
    Показать выпадающий список внутри поля ввода и сразу открыть его.
    """
 
    x = state_combobox.winfo_x()
    y = state_combobox.winfo_y()
    width = state_combobox.winfo_width()
    state_combobox.place(x=x, y=y, width=width)
    
    state_combobox.focus_set()
    state_combobox.event_generate("<Button-1>", x=0, y=0) 

def on_combobox_select(event):
    """
    Обработчик выбора из выпадающего списка.
    """
    selected_value = state_combobox.get()
    state_combobox.set(selected_value)
    search_process()

state_commands = [
    "/idle", "/zombie", "/running", "/sleeping", "/stopped", "/hanging", ":ports",
]

search_frame = tk.Frame(root)
search_frame.pack(side="bottom", pady=10, anchor="center")
search_frame.config(bg="#1e2120")

style = ttk.Style()
style.configure("TCombobox", fieldbackground="#1e2120", background="#1e2120", foreground="white", arrowsize=15)

search_label = tk.Label(
    search_frame, text="Search by PID or Name:", bg="#1e2120", fg="white"
)
search_label.pack(side="left")

state_combobox = ttk.Combobox(search_frame, values=state_commands, state="normal", style="TCombobox")
state_combobox.pack(side="left", padx=10)

search_button = tk.Button(search_frame, text="Search", command=search_process)
search_button.pack(side="left")
search_button.config(bg="#1e2120", foreground="white", activebackground="#1e2120")

state_combobox.bind("<Return>", lambda event: search_process())

state_combobox.bind("<KeyRelease>", filter_combobox)
state_combobox.bind("<<ComboboxSelected>>", on_combobox_select)

tree.bind("<Button-3>", lambda event: Context_Menu().create_context_menu(tree, event, processes_sorted))

update_data()
root.mainloop()