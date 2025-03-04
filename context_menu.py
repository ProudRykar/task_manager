import os
import signal
import tkinter as tk
from tkinter import messagebox

import psutil

from config import filtered_processes, processes_sorted

current_menu = None
global_hide_menu = None


def kill_process(pid):
    """Завершить процесс по PID (корректное завершение)"""
    global processes_sorted, filtered_processes
    try:
        process = psutil.Process(pid)
        process.terminate()
        messagebox.showinfo("Успех", f"Процесс {pid} завершен.")
    except psutil.NoSuchProcess:
        messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
    except psutil.AccessDenied:
        messagebox.showerror("Ошибка", f"Нет доступа для завершения процесса {pid}.")


def create_context_menu(tree, event, processes_sorted):
    """Создает контекстное меню для процесса при клике правой кнопкой мыши"""

    global current_menu
    global global_hide_menu

    def force_kill_process(pid):
        """Принудительно завершить процесс по PID (SIGKILL)"""
        global processes_sorted, filtered_processes
        try:
            process = psutil.Process(pid)
            process.kill()
            messagebox.showinfo("Успех", f"Процесс {pid} был принудительно завершен.")
        except psutil.NoSuchProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
        except psutil.AccessDenied:
            messagebox.showerror(
                "Ошибка", f"Нет доступа для завершения процесса {pid}."
            )
        except psutil.ZombieProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} является зомби.")

    def show_info(pid):
        """Показать информацию о процессе"""
        for proc in processes_sorted:
            if proc[0] == pid:
                messagebox.showinfo(
                    "Информация о процессе",
                    f"PID: {proc[0]}\nName: {proc[1]}\nCPU: {proc[2]}%\nMemory: {proc[3]}",
                )
                return

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


def bind_context_menu(tree, processes_sorted):
    """Привязка контекстного меню к правому клику мыши"""
    tree.bind(
        "<Button-3>", lambda event: create_context_menu(tree, event, processes_sorted)
    )
