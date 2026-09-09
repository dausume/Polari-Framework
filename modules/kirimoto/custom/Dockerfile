# Kiri:Moto (GridSpace/grid-apps) as an isle container — the upstream's own
# src/dock/Dockerfile mirrored at a PINNED commit (node 22, npm i, webpack-ext,
# pack-prod, @gridspace/app-server). All fetching happens at BUILD time; the
# running container fetches nothing (offline installs). ARG KIRIMOTO_COMMIT must
# be the full sha verified in AI-Notes/evaluations/PRINTER_STACK_GATE.md.
FROM node:22-slim AS src
ARG KIRIMOTO_COMMIT=<PIN ME>
RUN test "$KIRIMOTO_COMMIT" != "<PIN ME>" || { echo "KIRIMOTO_COMMIT is not pinned (licence gate first)"; exit 1; }
RUN apt-get -y update && apt-get -y install --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN git clone https://github.com/GridSpace/grid-apps.git /grid && cd /grid && git checkout "$KIRIMOTO_COMMIT" && rm -rf .git

FROM node:22-slim
WORKDIR /grid
COPY --from=src /grid/package.json /grid/app.js /grid/
COPY --from=src /grid/apps /grid/apps
COPY --from=src /grid/src /grid/src
COPY --from=src /grid/web /grid/web
COPY --from=src /grid/bin /grid/bin
COPY --from=src /grid/license.md /grid/license.md
RUN apt-get -y update && apt-get -y install --no-install-recommends curl git ca-certificates && rm -rf /var/lib/apt/lists/*
# upstream's package.json pulls one dependency over git+ssh (gridspace/basic-ftp); the build has no ssh keys → https
RUN git config --global url."https://github.com/".insteadOf "ssh://git@github.com/" \
    && git config --global url."https://github.com/".insteadOf "git@github.com:" --add
RUN npm i && npm run webpack-ext && mkdir -p src/pack && npm run pack-prod && npm install -g @gridspace/app-server && rm -rf /grid/bin
EXPOSE 8080
CMD ["gs-app-server"]
