ARG BUILD_FROM
FROM ${BUILD_FROM}

ARG BUILD_ARCH=amd64
ARG HA_CLI_VERSION="5.5.0"

RUN apk add --no-cache python3 py3-pip curl && \
    curl -fsSL -o /usr/bin/ha "https://github.com/home-assistant/cli/releases/download/${HA_CLI_VERSION}/ha_${BUILD_ARCH}" && \
    chmod +x /usr/bin/ha

COPY package /tmp/package
RUN pip3 install --no-cache-dir --break-system-packages /tmp/package && \
    rm -rf /tmp/package

COPY www /www
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
