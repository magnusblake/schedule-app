import sys
from PyQt5.uic import loadUi
import sqlite3
from PyQt5.QtWidgets import QApplication, QMainWindow, QHeaderView, QAbstractItemView, QMessageBox
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QIcon, QPixmap
from PyQt5.QtWidgets import QMainWindow, QApplication, QLabel
from datetime import datetime

class SchoolScheduleApp(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi('src/scheduleForm.ui', self)

        self.pushButton.clicked.connect(self.add_schedule_item)
        self.pushButton_2.clicked.connect(self.delete_schedule_item)

        # Определяем размер окна
        self.setFixedSize(self.width(), self.height())

        # Иконка приложения
        icon = QIcon()
        icon.addPixmap(QPixmap("src/schedule.ico"), QIcon.Selected, QIcon.On)
        self.setWindowIcon(icon)

        # Инициализация модели данных
        self.model = QStandardItemModel()
        self.tableView.setModel(self.model)

        self.tableView.verticalHeader().setDefaultSectionSize(50)
        self.tableView.horizontalHeader().setDefaultSectionSize(150)

        # Установка верхних заголовков
        self.model.setHorizontalHeaderLabels(['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'])

        # Установка боковых заголовков
        vertical_header_labels = ['1', '2', '3', '4', '5', '6', '7']
        self.model.setVerticalHeaderLabels(vertical_header_labels)

        # Установка режима изменения размеров
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # Запрещаем редактирование значений в таблице
        self.tableView.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Инициализация базы данных
        self.connection = sqlite3.connect('data/school.db')
        self.cursor = self.connection.cursor()
        self.create_tables()
        
        # Первоначальное заполнение комбобоксов и спинбоксов
        self.init_comboboxes_and_spinboxes()

        # Создание модели данных для лога изменений
        self.list_model = QStandardItemModel()
        self.listView.setModel(self.list_model)

        # Загрузка данных из файла log.txt в list_model
        self.load_log_from_file()

        # Первоначальное обновление таблицы при открытии вкладки "Просмотр расписания"
        self.scheduleWidget.currentChanged.connect(self.tab_changed)
        self.update_schedule_view()

        # Добавьте эти строки для получения ссылок на метки статистики
        self.label_total_classrooms = self.findChild(QLabel, 'label_10')
        self.label_total_teachers = self.findChild(QLabel, 'label_13')
        self.label_total_lessons_week = self.findChild(QLabel, 'label_14')
        self.label_total_subjects = self.findChild(QLabel, 'label_15')
        self.label_today_lessons = self.findChild(QLabel, 'label_16')
        self.label_db_records = self.findChild(QLabel, 'label_17')

        # Добавьте эту строку для подключения метода обновления статистики
        # к событию изменения вкладки
        self.scheduleWidget.currentChanged.connect(self.update_statistics)

        # Обновление статистики
        self.update_statistics()

    def init_comboboxes_and_spinboxes(self):
        self.comboBox.addItems(self.get_subjects())
        self.comboBox_2.addItems(self.get_teachers())
        self.comboBox_3.addItems(["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"])
        self.comboBox_4.addItems(["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"])

        # Настройка минимального и максимального значения спинбоксов
        self.spinBox.setMinimum(1)
        self.spinBox.setMaximum(self.comboBox_4.count())

        # Получение количества кабинетов из базы данных
        classrooms_count = len(self.get_classrooms())
        # Установка максимального значения спинбокса равным количеству кабинетов
        self.spinBox.setMaximum(classrooms_count)

        self.spinBox_2.setMinimum(1)
        self.spinBox_2.setMaximum(7)
        self.spinBox_3.setMinimum(1)
        self.spinBox_3.setMaximum(7)

    def create_tables(self):
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS subjects
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS teachers
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS cabinets
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, number TEXT, capacity INTEGER)''')
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS lessons
                               (id INTEGER PRIMARY KEY AUTOINCREMENT, day_of_week TEXT, lesson_number INTEGER,
                                subject_id INTEGER, teacher_id INTEGER, cabinet_id INTEGER,
                                FOREIGN KEY (subject_id) REFERENCES subjects(id),
                                FOREIGN KEY (teacher_id) REFERENCES teachers(id),
                                FOREIGN KEY (cabinet_id) REFERENCES cabinets(id))''')
        self.connection.commit()

        # Проверяем, есть ли данные в таблицах subjects, teachers, cabinets
        if not self.get_subjects():
            self.cursor.execute('''INSERT INTO subjects (name) VALUES ('Математика')''')
            self.cursor.execute('''INSERT INTO subjects (name) VALUES ('Физика')''')
            self.cursor.execute('''INSERT INTO subjects (name) VALUES ('История')''')
            self.cursor.execute('''INSERT INTO subjects (name) VALUES ('Литература')''')
            self.connection.commit()

        if not self.get_teachers():
            self.cursor.execute('''INSERT INTO teachers (name) VALUES ('Иванов')''')
            self.cursor.execute('''INSERT INTO teachers (name) VALUES ('Петров')''')
            self.cursor.execute('''INSERT INTO teachers (name) VALUES ('Сидоров')''')
            self.cursor.execute('''INSERT INTO teachers (name) VALUES ('Смирнов')''')
            self.connection.commit()

        if not self.get_classrooms():
            self.cursor.execute('''INSERT INTO cabinets (number, capacity) VALUES ('101', 30)''')
            self.cursor.execute('''INSERT INTO cabinets (number, capacity) VALUES ('102', 25)''')
            self.cursor.execute('''INSERT INTO cabinets (number, capacity) VALUES ('103', 35)''')
            self.cursor.execute('''INSERT INTO cabinets (number, capacity) VALUES ('104', 40)''')
            self.connection.commit()

    def add_schedule_item(self):
        subject = self.comboBox.currentText()
        teacher = self.comboBox_2.currentText()
        classroom = self.spinBox.value() 
        day_of_week = self.comboBox_3.currentText()
        lesson_number = self.spinBox_2.value()

        subject_id = self.get_subject_id(subject)
        teacher_id = self.get_teacher_id(teacher)
        cabinet_id = self.get_cabinet_id(classroom)

        # Проверяем, сколько уроков уже ведет преподаватель в выбранный день
        self.cursor.execute('''SELECT COUNT(*) FROM lessons 
                            WHERE day_of_week = ? AND teacher_id = ? AND availability = 1''', (day_of_week, teacher_id))
        teacher_lessons_count = self.cursor.fetchone()[0]

        if teacher_lessons_count >= 5:
            QMessageBox.warning(self, "Предупреждение", "Преподаватель уже ведёт 5 уроков в указанный день!")
            return

        # Проверяем, существует ли уже урок с таким же номером и днем недели
        self.cursor.execute('''SELECT COUNT(*) FROM lessons 
                            WHERE day_of_week = ? AND lesson_number = ? AND availability = 1''', (day_of_week, lesson_number))
        count = self.cursor.fetchone()[0]
        if count > 0:
            QMessageBox.warning(self, "Предупреждение", "Урок на данном месте уже существует, сначала удалите его!")
        else:
            # Вставляем запись в таблицу lessons
            self.cursor.execute('''INSERT INTO lessons (day_of_week, lesson_number, subject_id, teacher_id, cabinet_id)
                                VALUES (?, ?, ?, ?, ?)''', (day_of_week, lesson_number, subject_id, teacher_id, cabinet_id))
            self.connection.commit()

            self.update_schedule_view()

            QMessageBox.information(self, "Уведомление", "Вы добавили урок!")

            # Логирование действия
            self.log_action(f"[УСПЕШНО] Добавлен урок №{lesson_number} в {day_of_week} | {subject} | {teacher} | Кабинет {classroom}")

            # Обновление статистики
            self.update_statistics()

    def delete_schedule_item(self):
        lesson_number = self.spinBox_3.value()
        day_of_week = self.comboBox_4.currentText()

        # Проверяем, существует ли урок с указанным номером и выбранным днем недели
        self.cursor.execute('''SELECT COUNT(*) FROM lessons 
                            WHERE lesson_number = ? AND day_of_week = ? AND availability = 1''', (lesson_number, day_of_week))
        count = self.cursor.fetchone()[0]
        if count == 0:
            QMessageBox.warning(self, "Предупреждение", "Урок с указанным номером не найден!")
        else:
            # Обновляем значение столбца "доступность" на 0
            self.cursor.execute('''UPDATE lessons SET availability = 0 WHERE lesson_number = ?''', (lesson_number,))
            self.connection.commit()

            self.update_schedule_view()

            QMessageBox.information(self, "Уведомление", "Вы скрыли урок!")

            # Логирование действия
            self.log_action(f"[УСПЕШНО] Удалён урок №{lesson_number} в {day_of_week}")

            # Обновление статистики
            self.update_statistics()

    def update_schedule_view(self):
        self.cursor.execute('''SELECT day_of_week, lesson_number, subjects.name, teachers.name, cabinets.number
                            FROM lessons
                            JOIN subjects ON lessons.subject_id = subjects.id
                            JOIN teachers ON lessons.teacher_id = teachers.id
                            JOIN cabinets ON lessons.cabinet_id = cabinets.id
                            WHERE availability = 1''')  # Фильтр по доступности уроков

        schedule_data = self.cursor.fetchall()

        # Очищаем модель
        self.model.clear()

        # Обновляем верхние заголовки
        self.model.setHorizontalHeaderLabels(['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'])

        for row in schedule_data:
            day_of_week_index = self.comboBox_3.findText(row[0])  # Индекс дня недели в комбобоксе
            lesson_number_index = row[1] - 1  # Номер урока (от 1 до 7)

            # Создаем объект ячейки с данными
            item = QStandardItem(f"{row[2]}\n{row[3]}\nКабинет №{row[4]}")

            # Проверяем, есть ли уже объект в ячейке
            if self.model.item(lesson_number_index, day_of_week_index) is None:
                self.model.setItem(lesson_number_index, day_of_week_index, item)

        self.tableView.resizeColumnsToContents()

    def update_statistics(self):
        total_classrooms = len(self.get_classrooms())
        total_teachers = len(self.get_teachers())
        total_lessons_week = self.get_total_lessons_week()
        total_subjects = len(self.get_subjects())
        today_lessons = self.get_today_lessons()
        db_records = self.get_db_records()

        # Обновляем значения меток статистики
        self.label_total_classrooms.setText(f"Всего кабинетов: {total_classrooms}")
        self.label_total_teachers.setText(f"Всего преподавателей: {total_teachers}")
        self.label_total_lessons_week.setText(f"Всего уроков за неделю: {total_lessons_week}")
        self.label_total_subjects.setText(f"Всего предметов: {total_subjects}")
        self.label_today_lessons.setText(f"Уроки сегодня: {today_lessons}")
        self.label_db_records.setText(f"Записей в базе данных: {db_records}")

    def get_subjects(self):
        self.cursor.execute("SELECT name FROM subjects")
        subjects = self.cursor.fetchall()
        return [subject[0] for subject in subjects]
    
    def get_total_lessons_week(self):
        self.cursor.execute("SELECT COUNT(*) FROM lessons WHERE availability = 1")
        count = self.cursor.fetchone()[0]
        return count

    def get_today_lessons(self):
        # Получаем сегодняшний день недели
        today_weekday_index = datetime.today().weekday()

        # Преобразуем индекс дня недели в текстовое представление
        days_of_week = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
        today_weekday = days_of_week[today_weekday_index]

        # Запрос к базе данных для получения количества уроков на сегодня
        self.cursor.execute("SELECT COUNT(*) FROM lessons WHERE day_of_week = ? AND availability = 1", (today_weekday,))
        count = self.cursor.fetchone()[0]
        return count

    def get_db_records(self):
        # Получаем общее количество записей во всех таблицах базы данных
        tables = ['subjects', 'teachers', 'cabinets', 'lessons']
        total_records = 0
        for table in tables:
            self.cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = self.cursor.fetchone()[0]
            total_records += count
        return total_records

    def get_teachers(self):
        self.cursor.execute("SELECT name FROM teachers")
        teachers = self.cursor.fetchall()
        return [teacher[0] for teacher in teachers]

    def get_classrooms(self):
        self.cursor.execute("SELECT number FROM cabinets")
        classrooms = self.cursor.fetchall()
        return [str(classroom[0]) for classroom in classrooms]

    def get_subject_id(self, subject_name):
        self.cursor.execute("SELECT id FROM subjects WHERE name = ?", (subject_name,))
        subject_id = self.cursor.fetchone()
        if subject_id:
            return subject_id[0]
        else:
            return None

    def get_teacher_id(self, teacher_name):
        self.cursor.execute("SELECT id FROM teachers WHERE name = ?", (teacher_name,))
        teacher_id = self.cursor.fetchone()
        if teacher_id:
            return teacher_id[0]
        else:
            return None

    def get_cabinet_id(self, cabinet_number):
        self.cursor.execute("SELECT id FROM cabinets WHERE number = ?", (cabinet_number,))
        cabinet_id = self.cursor.fetchone()
        if cabinet_id:
            return cabinet_id[0]
        else:
            return None

    def load_log_from_file(self):
        try:
            with open('data/log.txt', 'r') as file:  # изменено 'a' на 'r'
                for line in file:
                    line = line.strip()
                    if line:
                        self.list_model.appendRow(QStandardItem(line))
        except FileNotFoundError:
            pass  # Обработка ситуации, когда файл log.txt отсутствует

    def log_action(self, log_message):
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        formatted_message = f"[{current_time}] {log_message}"
        
        # Добавление строки в лог изменений и запись в файл log.txt
        self.list_model.appendRow(QStandardItem(formatted_message))
        with open('data/log.txt', 'a') as file:
            file.write(formatted_message + '\n')

    def tab_changed(self, index):
        if index == 0:  # Вкладка "Просмотр расписания"
            self.update_schedule_view()

    def show_message_box(self, title, message):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()

    def closeEvent(self, event):
        # Закрытие файла log.txt
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SchoolScheduleApp()
    window.show()
    sys.exit(app.exec_())