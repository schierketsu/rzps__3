#!/bin/sh
# ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 5
# Резервное копирование БД: сразу после запуска и далее раз в сутки pg_dump сохраняет
# копию базы testdb в папку ./backups (на компьютере). Хранятся 7 последних копий.
# Восстановление: pg_restore -h localhost -U postgres_admin -d testdb --clean <файл .dump>

export PGHOST=db
export PGUSER=postgres_admin
export PGDATABASE=testdb
export PGSSLMODE=require
export PGPASSWORD="$(tr -d '\r\n' < /run/secrets/db_admin_password)"

# Ждём, пока СУБД начнёт принимать подключения
until pg_isready -q; do
    sleep 2
done

while true; do
    FILE="/backups/testdb_$(date +%Y-%m-%d_%H-%M).dump"
    if pg_dump --format=custom --file="$FILE"; then
        echo "Резервная копия создана: $FILE"
    else
        echo "ОШИБКА: резервная копия не создана" >&2
    fi
    # Удаляем старые копии, оставляем 7 последних
    ls -1t /backups/testdb_*.dump 2>/dev/null | tail -n +8 | xargs -r rm -f
    sleep 86400
done
