-- ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 4
-- Аудит изменений: каждое добавление, изменение и удаление строки в таблицах магазина
-- записывается в audit_log — кто (учётная запись БД), когда, в какой таблице, что было и что стало.
-- У app_user и app_manager нет прав на audit_log: они не могут ни прочитать, ни подделать журнал.
-- Посмотреть журнал (под postgres_admin): SELECT * FROM audit_log ORDER BY id;

CREATE TABLE audit_log (
    id         BIGSERIAL   PRIMARY KEY,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    db_user    TEXT        NOT NULL DEFAULT session_user,
    table_name TEXT        NOT NULL,
    operation  TEXT        NOT NULL,
    row_id     INTEGER,
    old_data   JSONB,
    new_data   JSONB
);

-- SECURITY DEFINER: функция выполняется с правами владельца (администратора),
-- поэтому может писать в audit_log, хотя у пользователей приложения такого права нет.
CREATE FUNCTION write_audit_log() RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
    INSERT INTO audit_log (table_name, operation, row_id, old_data, new_data)
    VALUES (
        TG_TABLE_NAME,
        TG_OP,
        CASE WHEN TG_OP = 'DELETE' THEN OLD.id ELSE NEW.id END,
        CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE to_jsonb(OLD) END,
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE to_jsonb(NEW) END
    );
    RETURN NULL;
END;
$$;

CREATE TRIGGER customers_audit AFTER INSERT OR UPDATE OR DELETE ON customers
    FOR EACH ROW EXECUTE FUNCTION write_audit_log();
CREATE TRIGGER products_audit AFTER INSERT OR UPDATE OR DELETE ON products
    FOR EACH ROW EXECUTE FUNCTION write_audit_log();
CREATE TRIGGER orders_audit AFTER INSERT OR UPDATE OR DELETE ON orders
    FOR EACH ROW EXECUTE FUNCTION write_audit_log();
CREATE TRIGGER order_items_audit AFTER INSERT OR UPDATE OR DELETE ON order_items
    FOR EACH ROW EXECUTE FUNCTION write_audit_log();
