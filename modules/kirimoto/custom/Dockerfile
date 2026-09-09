# Kiri:Moto (GridSpace/grid-apps) as an isle container — built from a PINNED commit,
# no runtime fetches (offline installs). ARG KIRIMOTO_COMMIT must be a full sha
# verified against AI-Notes/evaluations/PRINTER_STACK_GATE.md; the build refuses '<PIN ME>'.
FROM node:20-slim AS build
ARG KIRIMOTO_COMMIT=<PIN ME>
RUN test "$KIRIMOTO_COMMIT" != "<PIN ME>" || { echo "KIRIMOTO_COMMIT is not pinned (licence gate first)"; exit 1; }
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
WORKDIR /opt
RUN git clone https://github.com/GridSpace/grid-apps.git kirimoto && cd kirimoto && git checkout "$KIRIMOTO_COMMIT" && npm ci --omit=dev
FROM node:20-slim
WORKDIR /opt/kirimoto
COPY --from=build /opt/kirimoto /opt/kirimoto
EXPOSE 8080
# grid-apps serves kiri:moto at /kiri on its web port
CMD ["node", "src/main/gapp.js", "--port=8080"]
