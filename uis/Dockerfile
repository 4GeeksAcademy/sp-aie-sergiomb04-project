FROM node:20-bookworm-slim

WORKDIR /workspace/uis

COPY website/package.json website/package.json
COPY backoffice/package.json backoffice/package.json

RUN cd /workspace/uis/website && npm install
RUN cd /workspace/uis/backoffice && npm install

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

EXPOSE 3000 3001

CMD ["/usr/local/bin/start.sh"]
