import json
import os
import sys
# ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 3 (пауза между попытками входа)
import time
from datetime import datetime
from getpass import getpass

import psycopg
from psycopg import errors, sql


# Таблицы и колонки, с которыми разрешено работать.
# Пользователь выбирает их ТОЛЬКО из этого списка (по номеру), поэтому
# произвольный текст в название таблицы или колонки попасть не может.
TABLES = {
    "customers": ["id", "full_name", "email", "phone"],
    "products": ["id", "name", "category", "price"],
    "orders": ["id", "customer_id", "order_date", "status"],
    "order_items": ["id", "order_id", "product_id", "quantity", "price"],
}

# 6.7
LOG_FILE = os.getenv("LOG_FILE")

# ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 3
# Ограничение попыток входа: не больше 3 подряд, после неудачной — пауза (замедляет подбор пароля)
MAX_LOGIN_ATTEMPTS = 3
LOGIN_DELAY_SECONDS = 3


# ---------------------------------------------------------------- логи

def write_to_log_file(text):
    if not LOG_FILE:
        return
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as file:
        file.write(f"{time} {text}\n")


def log_info(message):
    print(f"[OK] {message}")  # stdout
    write_to_log_file(f"[INFO] {message}")


def log_error(message, error=None):
    # Пользователь видит только понятное сообщение (в stderr)
    print(f"[ОШИБКА] {message}", file=sys.stderr)
    # В файл пишем ещё и настоящий текст ошибки — чтобы разработчик мог разобраться
    if error is not None:
        message = f"{message} | {type(error).__name__}: {error}"
    write_to_log_file(f"[ERROR] {message}")


def friendly_error(error):
    """Превращает техническую ошибку БД в понятное пользователю сообщение."""
    if isinstance(error, errors.UniqueViolation):
        return "Такая запись уже существует."
    if isinstance(error, errors.ForeignKeyViolation):
        return "Ссылка на несуществующую запись (проверьте введённые id)."
    if isinstance(error, errors.NotNullViolation):
        return "Не заполнено обязательное поле."
    if isinstance(error, errors.CheckViolation):
        return "Недопустимое значение (например, отрицательная цена или количество)."
    if isinstance(error, errors.InsufficientPrivilege):
        return "Недостаточно прав для этой операции."
    if isinstance(error, psycopg.DataError):
        return "Неверный формат значения (например, буквы вместо числа или неверная дата)."
    if isinstance(error, psycopg.OperationalError):
        return "Нет связи с базой данных."
    return "Не удалось выполнить запрос."


# ---------------------------------------------------------------- ввод от пользователя

def print_options(options):
    for number, option in enumerate(options, start=1):
        print(f"  {number}. {option}")


def choose_one(title, options):
    """Показывает нумерованный список и возвращает один выбранный вариант."""
    print(f"\n{title}")
    print_options(options)
    while True:
        answer = input("Номер: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        print("Нет такого номера, попробуйте ещё раз.")


def choose_many(title, options):
    """То же самое, но можно выбрать несколько вариантов через запятую."""
    print(f"\n{title}")
    print_options(options)
    while True:
        answer = input("Номера через запятую (например: 1,3): ")
        parts = [part.strip() for part in answer.split(",")]
        all_correct = all(part.isdigit() and 1 <= int(part) <= len(options) for part in parts)
        if all_correct and len(set(parts)) == len(parts):
            return [options[int(part) - 1] for part in parts]
        print("Неверный ввод, попробуйте ещё раз.")


def ask_count(prompt):
    while True:
        answer = input(prompt).strip()
        if answer.isdigit() and int(answer) > 0:
            return int(answer)
        print("Введите целое число больше нуля.")


def choose_table():
    return choose_one("Выберите таблицу:", list(TABLES))


def columns_without_id(table):
    # id заполняется базой автоматически, его не вводим и не меняем
    return [column for column in TABLES[table] if column != "id"]


def print_rows(cursor):
    rows = cursor.fetchall()
    headers = [column.name for column in cursor.description]
    print()
    print(" | ".join(headers))
    print("-" * 60)
    for row in rows:
        print(" | ".join(str(value) for value in row))
    print(f"Найдено строк: {len(rows)}")


# ---------------------------------------------------------------- 6.1 просмотр
# 6.1.1
def show_all(cursor):
    table = choose_table()
    query = sql.SQL("SELECT * FROM {} ORDER BY id").format(sql.Identifier(table))
    cursor.execute(query)
    print_rows(cursor)

# 6.1.2
def show_filtered_by_one(cursor):
    table = choose_table()
    column = choose_one("По какой колонке фильтровать?", TABLES[table])
    value = input(f"Значение {column}: ")

    # SELECT * FROM "table" WHERE "column" = %s ORDER BY id
    query = sql.SQL("SELECT * FROM {} WHERE {} = %s ORDER BY id").format(
        sql.Identifier(table), sql.Identifier(column)
    )
    cursor.execute(query, [value])
    print_rows(cursor)

# 6.1.3
def show_filtered_by_many(cursor):
    table = choose_table()
    columns = choose_many("По каким колонкам фильтровать?", TABLES[table])
    values = [input(f"Значение {column}: ") for column in columns]

    # "col1" = %s AND "col2" = %s ...
    conditions = sql.SQL(" AND ").join(
        [sql.SQL("{} = %s").format(sql.Identifier(column)) for column in columns]
    )
    query = sql.SQL("SELECT * FROM {} WHERE {} ORDER BY id").format(
        sql.Identifier(table), conditions
    )
    cursor.execute(query, values)
    print_rows(cursor)


# ---------------------------------------------------------------- 6.2 обновление

#6.2.1
def update_one(cursor):
    table = choose_table()
    record_id = input("id записи, которую нужно изменить: ")
    columns = choose_many("Какие колонки изменить?", columns_without_id(table))
    values = [input(f"Новое значение {column}: ") for column in columns]

    # UPDATE "table" SET "col1" = %s, "col2" = %s WHERE id = %s
    assignments = sql.SQL(", ").join(
        [sql.SQL("{} = %s").format(sql.Identifier(column)) for column in columns]
    )
    query = sql.SQL("UPDATE {} SET {} WHERE id = %s").format(
        sql.Identifier(table), assignments
    )
    cursor.execute(query, values + [record_id])
    print(f"Изменено записей: {cursor.rowcount}")

#6.2.2
def update_many(cursor):
    table = choose_table()
    column = choose_one("Какую колонку изменить?", columns_without_id(table))
    new_value = input(f"Новое значение {column}: ")
    filter_column = choose_one("По какой колонке отобрать записи?", TABLES[table])
    text = input(f"Значения {filter_column} через запятую: ")
    filter_values = [value.strip() for value in text.split(",")]

    # UPDATE "table" SET "column" = %s WHERE "filter_column" IN (%s, %s, ...)
    # Для каждого значения из списка — свой плейсхолдер %s
    placeholders = sql.SQL(", ").join([sql.Placeholder()] * len(filter_values))
    query = sql.SQL("UPDATE {} SET {} = %s WHERE {} IN ({})").format(
        sql.Identifier(table),
        sql.Identifier(column),
        sql.Identifier(filter_column),
        placeholders,
    )
    cursor.execute(query, [new_value] + filter_values)
    print(f"Изменено записей: {cursor.rowcount}")


# ---------------------------------------------------------------- 6.3 и 6.4 вставка

def build_insert(table, columns):
    # INSERT INTO "table" ("col1", "col2") VALUES (%s, %s) RETURNING id
    return sql.SQL("INSERT INTO {} ({}) VALUES ({}) RETURNING id").format(
        sql.Identifier(table),
        sql.SQL(", ").join([sql.Identifier(column) for column in columns]),
        sql.SQL(", ").join([sql.Placeholder()] * len(columns)),
    )

#6.3.1
def insert_one(cursor):
    table = choose_table()
    columns = columns_without_id(table)
    values = [input(f"{column}: ") for column in columns]

    cursor.execute(build_insert(table, columns), values)
    new_id = cursor.fetchone()[0]
    print(f"Добавлена запись с id = {new_id}")

#6.4.1
def insert_many(cursor):
    table = choose_table()
    columns = columns_without_id(table)
    count = ask_count("Сколько строк добавить? ")
    query = build_insert(table, columns)

    new_ids = []
    for number in range(1, count + 1):
        print(f"Строка {number}:")
        values = [input(f"  {column}: ") for column in columns]
        cursor.execute(query, values)
        new_ids.append(cursor.fetchone()[0])
    print(f"Добавлены записи с id: {new_ids}")


def add_order(cursor, customer_id):
    """Создаёт заказ (дата и статус — по умолчанию) и возвращает его id."""
    cursor.execute(
        "INSERT INTO orders (customer_id) VALUES (%s) RETURNING id",
        [customer_id],
    )
    return cursor.fetchone()[0]


def add_order_item(cursor, order_id):
    """Спрашивает товар и добавляет его в заказ с номером order_id."""
    product_id = input("  id товара: ")
    quantity = input("  количество: ")
    price = input("  цена: ")
    cursor.execute(
        "INSERT INTO order_items (order_id, product_id, quantity, price) "
        "VALUES (%s, %s, %s, %s)",
        [order_id, product_id, quantity, price],
    )


def insert_order_with_item(cursor):
    customer_id = input("id покупателя: ")
    order_id = add_order(cursor, customer_id)  # id нового заказа из RETURNING
    print(f"Создан заказ id = {order_id}. Товар в заказе:")
    add_order_item(cursor, order_id)

#6.4.2
def insert_orders_with_items(cursor):
    orders_count = ask_count("Сколько заказов добавить? ")
    for number in range(1, orders_count + 1):
        print(f"\nЗаказ {number}")
        customer_id = input("id покупателя: ")
        order_id = add_order(cursor, customer_id)
        items_count = ask_count("Сколько товаров в заказе? ")
        for _ in range(items_count):
            add_order_item(cursor, order_id)
        print(f"Создан заказ id = {order_id}")


# ---------------------------------------------------------------- главное меню

MENU = {
    "Показать таблицу целиком": show_all,
    "Показать с фильтром по одной колонке": show_filtered_by_one,
    "Показать с фильтром по нескольким колонкам": show_filtered_by_many,
    "Изменить одну запись (по id)": update_one,
    "Изменить несколько записей (общее значение)": update_many,
    "Добавить одну строку в таблицу": insert_one,
    "Добавить заказ с товаром (2 связанные таблицы)": insert_order_with_item,
    "Добавить несколько строк в таблицу": insert_many,
    "Добавить несколько заказов с товарами": insert_orders_with_items,
    "Выход": None,
}


def load_config():
    with open("config.json", "r", encoding="utf-8") as file:
        return json.load(file)


# ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМАМИ 3 И 5
def connect_to_db(config):
    """Спрашивает логин и пароль и подключается к БД. Даёт не больше MAX_LOGIN_ATTEMPTS попыток."""
    for attempt in range(1, MAX_LOGIN_ATTEMPTS + 1):
        username = input("Введите логин БД: ")
        #6.6 getpass
        password = getpass("Введите пароль БД: ")

        connection_params = {
            "host": config["host"],
            "port": config["port"],
            "dbname": config["database"],
            "user": username,
            "password": password,
            # ПРОБЛЕМА 5: подключаемся только по зашифрованному каналу (TLS).
            # Если сервер не поддерживает TLS, подключения не будет.
            "sslmode": "require",
        }

        try:
            connection = psycopg.connect(**connection_params)
            log_info(f"Подключение к базе данных успешно (пользователь {username})")
            return connection
        except psycopg.Error as error:
            log_error("Не удалось подключиться к базе данных. Проверьте логин и пароль "
                      f"(попытка {attempt} из {MAX_LOGIN_ATTEMPTS}).", error)
            # ПРОБЛЕМА 3: пауза после неудачной попытки
            if attempt < MAX_LOGIN_ATTEMPTS:
                time.sleep(LOGIN_DELAY_SECONDS)

    log_error("Превышено число попыток входа. Работа завершена.")
    sys.exit(1)


def main():
    config = load_config()

    # ИЗМЕНЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМАМИ 3 И 5
    # (была одна попытка входа без ограничений и подключение без шифрования;
    #  теперь вход вынесен в connect_to_db: до 3 попыток с паузой и только по TLS)
    # username = input("Введите логин БД: ")
    # #6.6 getpass
    # password = getpass("Введите пароль БД: ")
    #
    # connection_params = {
    #     "host": config["host"],
    #     "port": config["port"],
    #     "dbname": config["database"],
    #     "user": username,
    #     "password": password
    # }
    #
    # try:
    #     connection = psycopg.connect(**connection_params)
    # except psycopg.Error as error:
    #     log_error("Не удалось подключиться к базе данных. Проверьте логин и пароль.", error)
    #     sys.exit(1)
    #
    # log_info(f"Подключение к базе данных успешно (пользователь {username})")
    connection = connect_to_db(config)

    with connection:
        while True:
            title = choose_one("Главное меню:", list(MENU))
            action = MENU[title]
            if action is None:
                break

            try:
                with connection.cursor() as cursor:
                    action(cursor)
                # Все запросы одного пункта меню — одна транзакция:
                # либо сохраняется всё, либо (при ошибке) ничего
                connection.commit()
                log_info(f"Запрос выполнен: {title}")
            except psycopg.Error as error:
                log_error(friendly_error(error), error)
                if connection.closed:
                    log_error("Соединение с базой данных потеряно. Перезапустите программу.")
                    break
                connection.rollback()

    print("Работа завершена.")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nРабота завершена.")
