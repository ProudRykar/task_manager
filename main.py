# -*- coding: utf-8 -*-

import time
import tkinter as tk
from tkinter import ttk, messagebox
import psutil
import pyperclip


class ContextMenu:
    """Класс для управления контекстным меню, отображаемым при правом клике на процесс в таблице."""

    def __init__(self, app):
        """
        Args:
            app (TaskManagerApp): Экземпляр основного приложения для взаимодействия с данными и интерфейсом.
        """
        self.app = app
        self.current_menu = None
        self.global_hide_menu = None

    def create_context_menu(self, tree, event):
        """
        Создает контекстное меню для выбранного процесса в таблице при правом клике мыши.

        Args:
            tree (ttk.Treeview): Таблица процессов, где отображается контекстное меню.
            event (tk.Event): Событие клика мыши, содержащее координаты.
        """
        item = tree.identify_row(event.y)
        if not item:
            return
        tree.selection_set(item)
        pid = int(tree.item(item)["values"][0])
        self._close_existing_menu()
        menu = self._build_menu(tree, pid)
        self._bind_menu_events(menu, tree)
        self._show_menu(menu, event)

    def _build_menu(self, tree, pid):
        """
        Создает само контекстное меню с командами 'Завершить процесс' и 'Убить'.

        Args:
            tree (ttk.Treeview): Таблица процессов, к которой привязывается меню.
            pid (int): Идентификатор процесса для завершения.

        Returns:
            tk.Menu: Созданное контекстное меню.
        """
        menu = tk.Menu(tree, tearoff=0, bg="#1e2120", fg="white")
        menu.add_command(label="Завершить процесс", command=lambda: self._terminate_process(pid))
        menu.add_command(label="Убить", command=lambda: self._force_kill_process(pid))
        return menu

    def _bind_menu_events(self, menu, tree):
        """
        Привязывает события к меню: уход мыши, вход мыши и клик вне меню для закрытия.

        Args:
            menu (tk.Menu): Контекстное меню, к которому привязываются события.
            tree (ttk.Treeview): Таблица процессов для отслеживания кликов.
        """
        menu.bind("<Leave>", self._on_leave)
        menu.bind("<Enter>", self._on_enter)
        tree.bind("<Button-1>", self._close_menu_on_click)

    def _show_menu(self, menu, event):
        """
        Отображает контекстное меню в месте клика мыши.

        Args:
            menu (tk.Menu): Контекстное меню для отображения.
            event (tk.Event): Событие клика мыши с координатами.
        """
        self.current_menu = menu
        self.current_menu.post(event.x_root, event.y_root)

    def _terminate_process(self, pid):
        """
        Пытается мягко завершить процесс по PID.

        Args:
            pid (int): Идентификатор процесса для завершения.
        """
        self._kill_process(pid, force=False)

    def _force_kill_process(self, pid):
        """
        Принудительно убивает процесс по PID.

        Args:
            pid (int): Идентификатор процесса для завершения.
        """
        self._kill_process(pid, force=True)

    def _kill_process(self, pid, force=False):
        """
        Основная функция завершения процесса: мягко или принудительно, в зависимости от force.

        Args:
            pid (int): Идентификатор процесса для завершения.
            force (bool): Если True, процесс завершается принудительно (kill), иначе мягко (terminate).

        Exceptions:
            psutil.NoSuchProcess: Если процесс с указанным PID не существует.
            psutil.AccessDenied: Если нет прав для завершения процесса.
            psutil.ZombieProcess: Если процесс является зомби.
        """
        try:
            process = psutil.Process(pid)
            if force:
                process.kill()
                messagebox.showinfo("Успех", f"Процесс {pid} был принудительно завершен.")
            else:
                process.terminate()
                messagebox.showinfo("Успех", f"Процесс {pid} завершен.")
            self.app.filtered_processes = [proc for proc in self.app.filtered_processes if proc[0] != pid]
            self.app.update_treeview()
        except psutil.NoSuchProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
        except psutil.AccessDenied:
            messagebox.showerror("Ошибка", f"Нет доступа для завершения процесса {pid}.")
        except psutil.ZombieProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} является зомби.")

    def _on_leave(self, event):
        """
        Скрывает меню через 3 секунды после того, как мышь ушла с него.

        Args:
            event (tk.Event): Событие ухода мыши с меню.
        """
        if self.global_hide_menu:
            event.widget.after_cancel(self.global_hide_menu)
        self.global_hide_menu = event.widget.after(3000, event.widget.unpost)

    def _on_enter(self, event):
        """
        Отменяет скрытие меню, если мышь вернулась на него.

        Args:
            event (tk.Event): Событие входа мыши на меню.
        """
        if self.global_hide_menu:
            event.widget.after_cancel(self.global_hide_menu)
            self.global_hide_menu = None

    def _close_menu_on_click(self, event):
        """
        Закрывает меню, если кликнули вне его.

        Args:
            event (tk.Event): Событие клика мыши.
        """
        self._close_existing_menu()

    def _close_existing_menu(self):
        """Закрывает текущее открытое меню, если оно существует."""
        if self.current_menu:
            self.current_menu.unpost()
            self.current_menu = None
        if self.global_hide_menu:
            if self.current_menu:
                self.current_menu.after_cancel(self.global_hide_menu)
            self.global_hide_menu = None


class TaskManagerApp:
    """Класс основного приложения Task Manager для отображения и управления процессами системы."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Task Manager")
        self.root.geometry("600x600")
        self.root.configure(background="#1e2120")

        self.current_sort_field = "memory"
        self.current_sort_order = True
        self.selected_pids = []
        self.processes_sorted = []
        self.filtered_processes = []
        self.is_search_active = False
        self.search_term = ""
        self.is_updating = False
        self.state_commands = ["/idle", "/zombie", "/running", "/sleeping", "/stopped", "/hanging", ":ports"]

        self._setup_ui()
        self.context_menu = ContextMenu(self)

    def _setup_ui(self):
        """Настраивает основной интерфейс приложения: таблицу и строку поиска."""
        self._setup_treeview()
        self._setup_search_frame()
        self.tree.bind("<Button-3>", lambda event: self.context_menu.create_context_menu(self.tree, event))
        self.tree.bind("<Double-1>", self.show_process_info)
        self.root.after(2000, self.update_data)

    def _setup_treeview(self):
        """Создает и настраивает таблицу для отображения процессов."""
        self.tree_frame = tk.Frame(self.root, bg="#1e2120")
        self.tree_frame.pack(expand=True, fill="both")

        self.scrollbar = tk.Scrollbar(self.tree_frame, orient="vertical")
        self.tree = ttk.Treeview(
            self.tree_frame,
            columns=("PID", "Name", "CPU %", "Memory", "Status"),
            show="headings",
            yscrollcommand=self.scrollbar.set,
        )
        self.tree.pack(expand=True, fill="both", side="left")
        self.scrollbar.config(command=self.tree.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.tree.heading("PID", text="PID", anchor="center", command=self.sort_by_pid)
        self.tree.column("PID", width=60, stretch=False, anchor="center")
        self.tree.heading("Name", text="Name", anchor="center", command=self.sort_by_name)
        self.tree.column("Name", width=100)
        self.tree.heading("CPU %", text="CPU %", anchor="center", command=self.sort_by_cpu)
        self.tree.column("CPU %", width=60, stretch=False, anchor="center")
        self.tree.heading("Memory", text="Memory", anchor="center", command=self.sort_by_memory)
        self.tree.column("Memory", width=150, stretch=False, anchor="center")
        self.tree.heading("Status", text="Status", anchor="center", command=self.sort_by_status)
        self.tree.column("Status", width=80, stretch=False, anchor="center")

        style = ttk.Style()
        style.configure("Treeview.Heading", background="#1e2120", foreground="green")
        style.configure("Treeview", background="#1e2120", fieldbackground="#1e2120", foreground="green")
        style.map("Treeview", background=[("selected", "#2d2f2e")])
        self.tree.configure(style="Treeview")

        self.tree.tag_configure("even", background="#1e2120", foreground="green")
        self.tree.tag_configure("odd", background="#1e2120", foreground="green")

    def _setup_search_frame(self):
        """Создает нижнюю панель с полем поиска и кнопкой."""
        self.search_frame = tk.Frame(self.root, bg="#1e2120")
        self.search_frame.pack(side="bottom", pady=10, anchor="center")

        search_label = tk.Label(self.search_frame, text="Search by PID or Name:", bg="#1e2120", fg="white")
        search_label.pack(side="left")

        style = ttk.Style()
        style.configure("TCombobox", fieldbackground="#1e2120", background="#1e2120", foreground="white", arrowsize=15)

        self.state_combobox = ttk.Combobox(self.search_frame, values=self.state_commands, state="normal", style="TCombobox")
        self.state_combobox.pack(side="left", padx=10)
        self.state_combobox.bind("<Return>", lambda event: self.search_process())
        self.state_combobox.bind("<KeyRelease>", self._filter_combobox)
        self.state_combobox.bind("<<ComboboxSelected>>", self._on_combobox_select)

        search_button = tk.Button(self.search_frame, text="Search", command=self.search_process, bg="#1e2120", fg="white", activebackground="#1e2120")
        search_button.pack(side="left")

    def update_treeview(self):
        """Обновляет содержимое таблицы процессов, сохраняя выделение."""
        self.selected_pids = [self.tree.item(item)["values"][0] for item in self.tree.selection()]
        for row in self.tree.get_children():
            self.tree.delete(row)

        for i, proc in enumerate(self.filtered_processes):
            tag = "even" if i % 2 == 0 else "odd"
            item = self.tree.insert("", "end", values=proc, tags=(tag,))
            if proc[0] in self.selected_pids:
                self.tree.selection_add(item)

    def update_data(self):
        """Обновляет данные о процессах каждые 2 секунды, если поиск не активен."""
        if self.is_search_active:
            self.root.after(2000, self.update_data)
            return

        processes = list(psutil.process_iter(["pid", "name", "cpu_percent", "memory_info", "status"]))
        self.processes_sorted = []
        for proc in processes:
            try:
                pid = proc.info["pid"]
                name = proc.info.get("name", "N/A")
                cpu = proc.info["cpu_percent"]
                memory = (proc.info["memory_info"].rss / 1024 / 1024) if proc.info["memory_info"] else 0
                status = proc.info.get("status", "N/A")
                self.processes_sorted.append((pid, name, f"{cpu:.2f}%", f"{memory:.2f} MB", status))
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError):
                continue

        if self.current_sort_field == "name":
            self.processes_sorted.sort(key=lambda proc: proc[1].lower(), reverse=self.current_sort_order)
        elif self.current_sort_field == "memory":
            self.processes_sorted.sort(key=lambda proc: float(proc[3].replace(" MB", "")), reverse=self.current_sort_order)
        elif self.current_sort_field == "cpu":
            self.processes_sorted.sort(key=lambda proc: float(proc[2].replace("%", "")), reverse=self.current_sort_order)
        elif self.current_sort_field == "pid":
            self.processes_sorted.sort(key=lambda proc: proc[0], reverse=self.current_sort_order)
        elif self.current_sort_field == "status":
            self.processes_sorted.sort(key=lambda proc: proc[4].lower(), reverse=self.current_sort_order)

        if self.is_search_active and self.search_term:
            if self.search_term.isdigit():
                self.filtered_processes = [proc for proc in self.processes_sorted if str(proc[0]) == self.search_term]
            else:
                self.filtered_processes = [proc for proc in self.processes_sorted if self.search_term in proc[1].lower()]
        else:
            self.filtered_processes = self.processes_sorted

        self.update_treeview()
        self.root.after(2000, self.update_data)

    def sort_processes_by_field(self, field: str, reverse: bool) -> None:
        """
        Сортирует процессы по указанному полю с учетом направления сортировки.

        Args:
            field (str): Поле для сортировки (pid, name, cpu, memory, status).
            reverse (bool): Направление сортировки (True для убывания, False для возрастания).
        """
        if self.current_sort_field == field:
            self.current_sort_order = not self.current_sort_order
        else:
            self.current_sort_field = field
            self.current_sort_order = reverse

        key_func = {
            "memory": lambda proc: float(proc[3].replace(" MB", "")),
            "name": lambda proc: proc[1].lower(),
            "cpu": lambda proc: float(proc[2].replace("%", "")),
            "pid": lambda proc: proc[0],
            "status": lambda proc: proc[4].lower()
        }.get(field)

        if key_func:
            self.processes_sorted.sort(key=key_func, reverse=self.current_sort_order)
            self.update_treeview()

    def sort_by_memory(self, event=None) -> None:
        """
        Сортирует процессы по использованию памяти.
        """
        self.sort_processes_by_field("memory", True)

    def sort_by_name(self, event=None) -> None:
        """
        Сортирует процессы по имени.
        """
        self.sort_processes_by_field("name", False)

    def sort_by_cpu(self, event=None) -> None:
        """
        Сортирует процессы по использованию CPU.
        """
        self.sort_processes_by_field("cpu", True)

    def sort_by_pid(self, event=None) -> None:
        """
        Сортирует процессы по PID.
        """
        self.sort_processes_by_field("pid", False)

    def sort_by_status(self, event=None) -> None:
        """
        Сортирует процессы по статусу.
        """
        self.sort_processes_by_field("status", False)

    def _filter_combobox(self, event=None) -> None:
        """
        Фильтрует варианты в выпадающем списке поиска по введенному тексту.

        Args:
            event (tk.Event, optional): Событие ввода текста (необязательно).
        """
        search_text = self.state_combobox.get().lower()
        filtered_commands = [command for command in self.state_commands if search_text in command.lower()]
        current_value = self.state_combobox.get()
        self.state_combobox['values'] = filtered_commands
        if not filtered_commands or current_value not in filtered_commands:
            self.state_combobox.set(current_value)

    def _on_combobox_select(self, event):
        """
        Обрабатывает выбор элемента в выпадающем списке и запускает поиск.

        Args:
            event (tk.Event): Событие выбора элемента в комбобоксе.
        """
        selected_value = self.state_combobox.get()
        self.state_combobox.set(selected_value)
        self.search_process()

    def search_process(self, event=None) -> None:
        """
        Ищет процессы по PID, имени или фильтрует по состоянию/портам.

        Args:
            event (tk.Event, optional): Событие, вызывающее поиск (необязательно).
        """
        self.search_term = self.state_combobox.get().strip().lower()
        if self.search_term:
            self.is_search_active = True

            state_commands = {
                '/idle': 'idle',
                '/zombie': 'zombie',
                '/running': 'running',
                '/sleeping': 'sleeping',
                '/stopped': 'stopped',
                '/hanging': 'hanging'
            }

            if self.search_term in state_commands:
                target_state = state_commands[self.search_term]
                self.filtered_processes = [
                    proc for proc in self.processes_sorted
                    if len(proc) > 4 and proc[4].lower() == target_state
                ]
            elif self.search_term == "/hanging":
                self.filtered_processes = [
                    proc for proc in self.processes_sorted if len(proc) > 4 and self.is_process_hanging(proc)
                ]
            elif self.search_term == ":ports":
                processes_with_ports = self.find_processes_with_ports()
                self.filtered_processes = [
                    proc for proc in self.processes_sorted if proc[0] in processes_with_ports
                ]
            elif ":" in self.search_term and self.search_term != "/ports":
                port_str = self.search_term.lstrip(":")
                if port_str.isdigit():
                    process_by_port = self.find_process_by_port(int(port_str))
                    if process_by_port:
                        self.filtered_processes = [
                            proc for proc in self.processes_sorted if proc[0] == process_by_port[1]
                        ]
                    else:
                        self.filtered_processes = []
                else:
                    self.filtered_processes = []
            else:
                if self.search_term.isdigit():
                    self.filtered_processes = [
                        proc for proc in self.processes_sorted if str(proc[0]) == self.search_term
                    ]
                else:
                    self.filtered_processes = [
                        proc for proc in self.processes_sorted if self.search_term in proc[1].lower()
                    ]
        else:
            self.is_search_active = False
            self.filtered_processes = self.processes_sorted

        self.update_treeview()

    def is_process_hanging(self, proc) -> bool:
        """
        Проверяет, завис ли процесс (неактивен более часа).

        Args:
            proc (tuple): Кортеж с информацией о процессе.

        Returns:
            bool: True, если процесс завис, иначе False.

        Exceptions:
            IndexError: Если в кортеже proc недостаточно элементов.
        """
        try:
            last_active_time = proc[5]
            current_time = time.time()
            idle_threshold = 3600
            return (current_time - last_active_time) > idle_threshold
        except IndexError:
            return False

    def find_processes_with_ports(self) -> set:
        """
        Находит процессы, которые слушают порты.

        Returns:
            set: Множество PID процессов, слушающих порты.
        """
        connections = psutil.net_connections(kind="inet")
        processes_with_ports = set()
        for conn in connections:
            if conn.status == "LISTEN" and conn.pid is not None:
                processes_with_ports.add(conn.pid)
        return processes_with_ports

    def find_process_by_port(self, port) -> (tuple[str, int] | None):
        """
        Ищет процесс, который слушает указанный порт.

        Args:
            port (int): Номер порта для поиска.

        Returns:
            tuple[str, int] | None: Кортеж с именем процесса и PID, если найден, иначе None.

        Exceptions:
            psutil.NoSuchProcess: Если процесс с найденным PID больше не существует.
        """
        connections = psutil.net_connections(kind="inet")
        for conn in connections:
            if conn.status == "LISTEN" and conn.laddr.port == port:
                pid = conn.pid
                try:
                    process = psutil.Process(pid)
                    return (process.name(), pid)
                except psutil.NoSuchProcess:
                    continue
        return None

    def show_process_info(self, event) -> None:
        """
        Показывает подробную информацию о процессе при двойном клике.

        Args:
            event (tk.Event): Событие двойного клика мыши.
        """
        selected_item = self.tree.selection()[0]
        selected_pid = self.tree.item(selected_item)["values"][0]
        for proc in self.filtered_processes:
            if proc[0] == selected_pid:
                self.display_process_info(proc)
                break

    def copy_pid_to_clipboard(self, proc) -> None:
        """
        Копирует PID процесса в буфер обмена.

        Args:
            proc (tuple): Кортеж с информацией о процессе, включая PID.
        """
        pyperclip.copy(proc[0])
        print("PID copied to clipboard")

    def start_update_process_info(self) -> None:
        """Запускает обновление информации о процессе."""
        self.is_updating = True

    def stop_update_process_info(self) -> None:
        """Останавливает обновление информации о процессе."""
        self.is_updating = False

    def update_process_info(self, proc, info_frame, labels=None) -> None:
        """
        Обновляет данные о процессе в окне информации каждую секунду.

        Args:
            proc (tuple): Кортеж с информацией о процессе.
            info_frame (tk.Frame): Фрейм для отображения информации.
            labels (dict, optional): Словарь с метками для обновления данных (если None, создаются новые).

        Exceptions:
            psutil.NoSuchProcess: Если процесс больше не существует.
            psutil.AccessDenied: Если доступ к процессу запрещен.
        """
        if not self.is_updating:
            return
        try:
            process = psutil.Process(proc[0])
            cpu = process.cpu_percent(interval=0.5)
            start_time = process.create_time()
            active_time_seconds = int(time.time() - start_time)
            active_time = f"{active_time_seconds // 3600}h {active_time_seconds % 3600 // 60}m {active_time_seconds % 60}s"
            memory = process.memory_info().rss / 1024 / 1024
            status = process.status()
            port = None
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN" and conn.pid == proc[0]:
                    port = conn.laddr.port
                    break

            if labels is None:
                title_label = tk.Label(info_frame, text="Process Information", font=("Arial", 16, "bold"),
                                       bg="#1e2120", fg="green")
                title_label.pack(pady=10)

                info_section = tk.LabelFrame(info_frame, text="Details", bg="#1e2120", fg="green",
                                             font=("Arial", 12, "bold"), padx=20, pady=20)
                info_section.pack(expand=True, fill="both", pady=10)

                pid_label = tk.Label(info_section, text=f"PID: {proc[0]}", bg="#1e2120", fg="white", font=("Arial", 10))
                pid_label.grid(row=0, column=0, sticky="w", padx=10, pady=5)

                save_pid_button = tk.Button(info_section, text="Copy",
                                            command=lambda: self.copy_pid_to_clipboard(proc),
                                            borderwidth=0, bg="#1e2120", fg="green", relief="flat",
                                            activebackground="#2d2f2e")
                save_pid_button.grid(row=0, column=1, padx=10)

                name_label = tk.Label(info_section, text=f"Name: {proc[1]}", bg="#1e2120", fg="white", font=("Arial", 10))
                name_label.grid(row=1, column=0, sticky="w", padx=10, pady=5)

                cpu_label = tk.Label(info_section, text=f"CPU Usage: {cpu:.2f}%", bg="#1e2120", fg="white", font=("Arial", 10))
                cpu_label.grid(row=2, column=0, sticky="w", padx=10, pady=5)

                memory_label = tk.Label(info_section, text=f"Memory Usage: {memory:.2f} MB", bg="#1e2120", fg="white",
                                        font=("Arial", 10))
                memory_label.grid(row=3, column=0, sticky="w", padx=10, pady=5)

                time_label = tk.Label(info_section, text=f"Active Time: {active_time}", bg="#1e2120", fg="white",
                                      font=("Arial", 10))
                time_label.grid(row=4, column=0, sticky="w", padx=10, pady=5)

                status_label = tk.Label(info_section, text=f"Status: {status}", bg="#1e2120", fg="white",
                                        font=("Arial", 10))
                status_label.grid(row=5, column=0, sticky="w", padx=10, pady=5)

                if port:
                    port_label = tk.Label(info_section, text=f"Port: {port}", bg="#1e2120", fg="white",
                                          font=("Arial", 10))
                    port_label.grid(row=6, column=0, sticky="w", padx=10, pady=5)
                else:
                    port_label = None

                back_button = tk.Button(info_frame, text="Back",
                                        command=lambda: self.back_to_process_list(info_frame),
                                        font=("Arial", 12), bg="#1e2120", fg="green",
                                        activebackground="#2d2f2e", relief="flat", padx=10, pady=5)
                back_button.pack(pady=20)

                labels = {
                    "cpu": cpu_label,
                    "memory": memory_label,
                    "active_time": time_label,
                    "status": status_label,
                    "port": port_label,
                }
            else:
                labels["cpu"].config(text=f"CPU Usage: {cpu:.2f}%")
                labels["memory"].config(text=f"Memory Usage: {memory:.2f} MB")
                labels["active_time"].config(text=f"Active Time: {active_time}")
                labels["status"].config(text=f"Status: {status}")
                if port and labels.get("port"):
                    labels["port"].config(text=f"Port: {port}")

            if self.is_updating:
                self.root.after(1000, lambda: self.update_process_info(proc, info_frame, labels))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            self.back_to_process_list(info_frame)

    def display_process_info(self, proc) -> None:
        """
        Отображает окно с подробной информацией о процессе.

        Args:
            proc (tuple): Кортеж с информацией о процессе.
        """
        self.tree_frame.pack_forget()
        self.start_update_process_info()
        info_frame = tk.Frame(self.root, bg="#1e2120")
        info_frame.pack(expand=True, fill="both", padx=20, pady=20)
        self.update_process_info(proc, info_frame)

    def back_to_process_list(self, info_frame) -> None:
        """
        Возвращает к списку процессов из окна информации.

        Args:
            info_frame (tk.Frame): Фрейм окна информации для скрытия.
        """
        info_frame.pack_forget()
        self.stop_update_process_info()
        self.tree_frame.pack(expand=True, fill="both")

    def run(self) -> None:
        self.root.mainloop()


if __name__ == "__main__":
    app = TaskManagerApp()
    app.run()