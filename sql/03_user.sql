-- Пользователь для приложения (НЕ администратор)
-- ИЗМЕНЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 1
-- (пароль был записан в скрипте открытым текстом и опубликован в репозитории)
-- CREATE USER app_user WITH PASSWORD 'AppPassword123';
-- ИЗМЕНЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 3
-- Новый сложный пароль читается из секрета Docker (файл secrets/app_user_password.txt),
-- одновременно не больше 5 подключений под этой учётной записью.
\set app_user_password `tr -d '\r\n' < /run/secrets/app_user_password`
CREATE USER app_user WITH PASSWORD :'app_user_password' CONNECTION LIMIT 5;

-- Может подключаться к базе testdb и обращаться к схеме public
GRANT CONNECT ON DATABASE testdb TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;

-- ИЗМЕНЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 4
-- (оператор мог изменять любые колонки любых таблиц: цены, привязку заказа к покупателю и т. д.)
-- -- Может читать, добавлять и изменять данные.
-- -- НЕ может удалять строки (DELETE) и менять структуру (CREATE/DROP/ALTER).
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO app_user;

-- app_user — ОПЕРАТОР. Читает все таблицы магазина, добавляет покупателей и заказы.
-- Изменять может только то, что нужно в работе: контакты покупателя, статус заказа,
-- количество товара в позиции. Цены, товары и привязку заказов менять НЕ может.
GRANT SELECT ON customers, products, orders, order_items TO app_user;
GRANT INSERT ON customers, orders, order_items TO app_user;
GRANT UPDATE (full_name, email, phone) ON customers TO app_user;
GRANT UPDATE (status) ON orders TO app_user;
GRANT UPDATE (quantity) ON order_items TO app_user;

-- Нужно для SERIAL: при INSERT новый id берётся из последовательности
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 4
-- app_manager — МЕНЕДЖЕР. Отдельная учётная запись с прежними правами app_user:
-- может добавлять и изменять любые данные, включая цены и товары.
-- Удалять строки и менять структуру таблиц по-прежнему нельзя.
\set app_manager_password `tr -d '\r\n' < /run/secrets/app_manager_password`
CREATE USER app_manager WITH PASSWORD :'app_manager_password' CONNECTION LIMIT 5;
GRANT CONNECT ON DATABASE testdb TO app_manager;
GRANT USAGE ON SCHEMA public TO app_manager;
GRANT SELECT, INSERT, UPDATE ON customers, products, orders, order_items TO app_manager;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_manager;
