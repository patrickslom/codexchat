FROM node:22-bookworm-slim AS codexcli
RUN npm install -g --include=optional @openai/codex

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NODE_PATH=/usr/local/lib/node_modules

WORKDIR /app

COPY --from=codexcli /usr/local/bin/node /usr/local/bin/node
COPY --from=codexcli /usr/local/bin/npm /usr/local/bin/npm
COPY --from=codexcli /usr/local/bin/npx /usr/local/bin/npx
COPY --from=codexcli /usr/local/bin/codex /usr/local/bin/codex
COPY --from=codexcli /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -sf /usr/local/lib/node_modules /usr/local/lib/node
RUN ln -sf /usr/local/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64 \
    /usr/local/lib/node_modules/@openai/codex-linux-x64

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
