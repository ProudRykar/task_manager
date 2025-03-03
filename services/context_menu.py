import tkinter as tk
from tkinter import messagebox
import psutil
import os
import signal

# Глобальная переменная для хранения текущего контекстного меню
current_menu = None
global_hide_menu = None

def create_context_menu(tree, event, processes_sorted):
    """Создает контекстное меню для процесса при клике правой кнопкой мыши"""

    global current_menu
    global global_hide_menu

    def kill_process(pid):
        """Завершить процесс по PID (корректное завершение)"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            messagebox.showinfo("Успех", f"Процесс {pid} завершен.")
        except psutil.NoSuchProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
        except psutil.AccessDenied:
            messagebox.showerror("Ошибка", f"Нет доступа для завершения процесса {pid}.")

    def force_kill_process(pid):
        """Принудительно завершить процесс по PID (SIGKILL)"""
        try:
            process = psutil.Process(pid)
            process.kill()  # Принудительное завершение процесса
            messagebox.showinfo("Успех", f"Процесс {pid} был принудительно завершен.")
        except psutil.NoSuchProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} не существует.")
        except psutil.AccessDenied:
            messagebox.showerror("Ошибка", f"Нет доступа для завершения процесса {pid}.")
        except psutil.ZombieProcess:
            messagebox.showerror("Ошибка", f"Процесс {pid} является зомби.")

    def show_info(pid):
        """Показать информацию о процессе"""
        for proc in processes_sorted:
            if proc[0] == pid:
                messagebox.showinfo("Информация о процессе", f"PID: {proc[0]}\nName: {proc[1]}\nCPU: {proc[2]}%\nMemory: {proc[3]}")
                return

    # Получаем выбранный элемент
    item = tree.identify_row(event.y)
    if not item:
        return  

    # Явное выделение строки перед открытием меню
    tree.selection_set(item)

    # Создаем контекстное меню
    menu = tk.Menu(tree, tearoff=0)
    menu.config(background='#1e2120', foreground='white')  # Настроим цвет фона и текста
    pid = int(tree.item(item)['values'][0])  # Получаем PID из выбранной строки

    # Добавляем команды в меню
    menu.add_command(label="Завершить процесс", command=lambda: kill_process(pid))
    menu.add_command(label="Убить", command=lambda: force_kill_process(pid))  # Кастомный kill
    menu.add_command(label="Показать информацию", command=lambda: show_info(pid))
    
    def on_leave(event):
        global global_hide_menu
        # Отменяем предыдущий таймер, если он существует
        if global_hide_menu:
            menu.after_cancel(global_hide_menu)
            global_hide_menu = None

        # Получаем текущие координаты курсора
        x, y = menu.winfo_pointerxy()

        # Проверяем, находится ли курсор за пределами меню
        if not (x >= menu.winfo_rootx() and x <= menu.winfo_rootx() + menu.winfo_width() \
                and y >= menu.winfo_rooty() and y <= menu.winfo_rooty() + menu.winfo_height()):
            # Если курсор за пределами меню, запускаем таймер на закрытие через 3 секунды
            global_hide_menu = menu.after(3000, menu.unpost)

    def on_enter(event):
        global global_hide_menu
        # Отменяем таймер закрытия, если курсор вернулся в меню
        if global_hide_menu:
            menu.after_cancel(global_hide_menu)
            global_hide_menu = None

    def close_menu(event):
        """Закрывает контекстное меню при левом клике"""
        if current_menu:
            current_menu.unpost()

    # Привязываем события
    menu.bind("<Leave>", on_leave)
    menu.bind("<Enter>", on_enter)
    tree.bind("<Button-1>", close_menu)  # Закрыть меню при левом клике

    # Закрываем предыдущее контекстное меню, если оно было открыто
    if current_menu:
        current_menu.unpost()

    # Сохраняем текущее меню в глобальную переменную
    current_menu = menu

    # Открываем контекстное меню в точке клика
    menu.post(event.x_root, event.y_root)


def bind_context_menu(tree, processes_sorted):
    """Привязка контекстного меню к правому клику мыши"""
    tree.bind("<Button-3>", lambda event: create_context_menu(tree, event, processes_sorted))