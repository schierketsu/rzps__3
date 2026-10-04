FROM postgres:18

RUN localedef -i ru_RU -c -f UTF-8 \
    -A /usr/share/locale/locale.alias \
    ru_RU.UTF-8

ENV LANG=ru_RU.UTF-8

# ДОБАВЛЕНО ПО ЛАБОРАТОРНОЙ РАБОТЕ 4 В СООТВЕТСТВИИ С ПРОБЛЕМОЙ 5
# Собственный TLS-сертификат сервера (самоподписанный). Создаётся заново при каждой сборке образа,
# поэтому ключ уникален, а не тот, что лежит в общедоступном образе postgres.
# Подключается в compose.yaml параметрами ssl_cert_file / ssl_key_file.
RUN make-ssl-cert generate-default-snakeoil --force-overwrite