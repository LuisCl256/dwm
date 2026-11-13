FROM rabbitmq:4.1
RUN rabbitmq-plugins enable --offline rabbitmq_stomp
COPY rabbitmq/start.sh /usr/local/bin/flor-rabbit-start
RUN chmod +x /usr/local/bin/flor-rabbit-start
ENTRYPOINT ["/usr/local/bin/flor-rabbit-start"]
