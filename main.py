import tkinter as tk
from tkinter import ttk

import psutil
import pyperclip

from context_menu import bind_context_menu

current_sort_field = "memory"
current_sort_order = True
selected_pids = []
processes_sorted: list[int] = []
filtered_processes: list[int] = []
is_search_active = False
search_term = ""


def sort_by_memory(event=None):
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


def sort_by_name(event=None):
    """Сортировка по имени"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "name":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "name"
        current_sort_order = False
    processes_sorted.sort(key=lambda proc: proc[1].lower(), reverse=current_sort_order)
    update_treeview()


def sort_by_cpu(event=None):
    """Сортировка по CPU"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "cpu":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "cpu"
        current_sort_order = True
    processes_sorted.sort(key=lambda proc: proc[2], reverse=current_sort_order)
    update_treeview()


def sort_by_pid(event=None):
    """Сортировка по PID"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "pid":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "pid"
        current_sort_order = False
    processes_sorted.sort(key=lambda proc: proc[0], reverse=current_sort_order)
    update_treeview()


def sort_by_status(event=None):
    """Сортировка по статусу"""
    global processes_sorted, current_sort_field, current_sort_order
    if current_sort_field == "status":
        current_sort_order = not current_sort_order
    else:
        current_sort_field = "status"
        current_sort_order = False
    processes_sorted.sort(key=lambda proc: proc[4].lower(), reverse=current_sort_order)
    update_treeview()


def update_treeview():
    """Функция для обновления данных в Treeview"""
    global selected_pids, filtered_processes

    selected_pids = [tree.item(item)["values"][0] for item in tree.selection()]

    for row in tree.get_children():
        tree.delete(row)

    for i, proc in enumerate(filtered_processes):
        tag = "even" if i % 2 == 0 else "odd"
        item = tree.insert("", "end", values=proc, tags=(tag,))

        if proc[0] in selected_pids:
            tree.selection_add(item)


def find_processes_with_ports():
    """Функция для поиска всех процессов с открытыми портами"""
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


def search_process(event=None):
    """Функция для поиска процесса по PID, имени, порту, состоянию или вывода всех процессов с портами"""
    global filtered_processes, is_search_active, search_term

    search_term = search_entry.get().strip().lower()

    if search_term:
        is_search_active = True

        state_commands = {
            '/idle': 'idle',
            '/zombie': 'zombie',
            '/running': 'running',
            '/sleeping': 'sleeping',
            '/stopped': 'stopped'
        }

        if search_term in state_commands:
            target_state = state_commands[search_term]

            filtered_processes = [
                proc for proc in processes_sorted 
                if len(proc) > 4 and proc[4].lower() == target_state
            ]

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


def find_process_by_port(port):
    """Функция для поиска процесса по порту"""
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


def update_data():
    """Функция для обновления списка процессов"""
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


def show_process_info(event):
    """Функция для отображения информации о выбранном процессе"""
    selected_item = tree.selection()[0]
    selected_pid = tree.item(selected_item)["values"][0]

    for proc in filtered_processes:
        if proc[0] == selected_pid:
            display_process_info(proc)
            break


def save_pid_to_clipboard(proc):
    """Функция для сохранения PID в буфер обмена"""
    pid_info = proc[0]
    pyperclip.copy(pid_info)
    print("PID copied to clipboard")


is_updating = False


def start_update_process_info():
    """Запуск обновлений информации о процессе"""
    global is_updating
    is_updating = True


def stop_update_process_info():
    """Остановка обновлений информации о процессе"""
    global is_updating
    is_updating = False


def update_process_info(proc, info_frame, labels=None):
    """Функция для обновления информации о процессе в реальном времени без мерцания"""
    if not is_updating:
        return

    try:
        process = psutil.Process(proc[0])
        cpu = process.cpu_percent(interval=0.5)
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
                relief="flat",
                activebackground="#2d2f2e",
                highlightbackground="#1e2120",
                activeforeground="green",
            )
            save_pid_button.grid(row=0, column=1, padx=10)

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

            status_label = tk.Label(
                info_section,
                text=f"Status: {status}",
                bg="#1e2120",
                fg="white",
                font=("Arial", 10),
            )
            status_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)

            if port:
                port_label = tk.Label(
                    info_section,
                    text=f"Port: {port}",
                    bg="#1e2120",
                    fg="white",
                    font=("Arial", 10),
                )
                port_label.grid(row=5, column=0, sticky="w", padx=10, pady=5)

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
                "status": status_label,
                "port": (port_label if port else None),
            }

        labels["cpu"].config(text=f"CPU Usage: {cpu:.2f}%")
        labels["memory"].config(text=f"Memory Usage: {memory:.2f} MB")
        labels["status"].config(text=f"Status: {status}")
        if port:
            labels["port"].config(text=f"Port: {port}")

        if is_updating:
            root.after(1000, lambda: update_process_info(proc, info_frame, labels))

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        back_to_process_list(info_frame)


def display_process_info(proc):
    """Функция для отображения подробной информации о процессе"""
    tree_frame.pack_forget()
    start_update_process_info()
    info_frame = tk.Frame(root, bg="#1e2120")
    info_frame.pack(expand=True, fill="both", padx=20, pady=20)
    update_process_info(proc, info_frame)


def back_to_process_list(info_frame):
    """Функция для возврата к списку процессов"""
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

bind_context_menu(tree, processes_sorted)
tree.bind("<Double-1>", show_process_info)

search_frame = tk.Frame(root)
search_frame.pack(side="bottom", pady=10, anchor="center")
search_frame.config(bg="#1e2120")

search_label = tk.Label(
    search_frame, text="Search by PID or Name:", bg="#2e2e2e", fg="white"
)
search_label.pack(side="left")
search_label.config(bg="#1e2120", foreground="white")

search_entry = ttk.Entry(search_frame, style="TEntry")
style.configure(
    "TEntry", fieldbackground="#1e2120", foreground="white", insertcolor="white"
)
search_entry.pack(side="left", padx=10)

search_button = tk.Button(search_frame, text="Search", command=search_process)
search_button.pack(side="left")
search_button.config(bg="#1e2120", foreground="white", activebackground="#1e2120")

search_entry.bind("<Return>", lambda event: search_process())


update_data()
root.mainloop()
