#!/bin/sh
set -eu
# Broker aislado: AMQP y panel de gestión desactivados; solo STOMP en red interna.
# Token URL-safe generado localmente, nunca empaquetado ni expuesto como variable.
password="$(cat /run/secrets/rabbitmq-password)"
umask 077
cat > /etc/rabbitmq/conf.d/90-flor.conf <<EOF
listeners.tcp = none
stomp.listeners.tcp.1 = 61613
default_user = flor_service
default_pass = ${password}
EOF
unset password
chmod 0640 /etc/rabbitmq/conf.d/90-flor.conf
chown rabbitmq:rabbitmq /etc/rabbitmq/conf.d/90-flor.conf
exec /usr/local/bin/docker-entrypoint.sh rabbitmq-server
