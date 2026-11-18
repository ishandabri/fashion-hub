ifeq ($(OS),Windows_NT)
SHELL := C:/Progra~1/Git/bin/sh.exe
.SHELLFLAGS := -lc
else
SHELL := /bin/sh
endif

ifneq (,$(wildcard .env.deploy))
include .env.deploy
export
endif

APP_NAME ?= fashion-hub
BRANCH ?= main
COMPOSE_FILE ?= docker-compose.yml
ENV_FILE ?= .env
WEB_PORT ?= 6001
DEPLOY_TARGET ?= raspi
MAKE_CMD ?= make
LOCAL_APP_ENV ?= development
DEPLOY_APP_ENV ?= production

RASPI_HOST ?= raspi
RASPI_REPO_PATH ?= /home/ishan/projects/fashion-hub

.PHONY: help preflight preflight-local preflight-raspi preflight-host preflight-repo preflight-env preflight-compose preflight-port deploy deploy-local deploy-raspi local-up local-down status logs-api logs-frontend

help:
	@echo "Available targets:"
	@echo "  preflight         Validate the selected target (DEPLOY_TARGET=local|raspi)."
	@echo "  deploy            Preflight and deploy the selected target (DEPLOY_TARGET=local|raspi)."
	@echo "  preflight-local   Validate Docker, .env, Compose, and the local web port."
	@echo "  deploy-local      Build and start the local Docker stack."
	@echo "  preflight-raspi   Validate SSH, Docker, remote repo, .env, and Compose."
	@echo "  deploy-raspi      Pull main and build/start the stack on the Raspberry Pi."
	@echo "  local-up          Alias for deploy-local."
	@echo "  local-down        Stop the local Docker stack."
	@echo "  status            Show stack status for the selected target."
	@echo "  logs-api          Follow API logs for the selected target."
	@echo "  logs-frontend     Follow frontend logs for the selected target."
	@echo ""
	@echo "Examples:"
	@echo "  make preflight"
	@echo "  make deploy"
	@echo "  make preflight DEPLOY_TARGET=local"
	@echo "  make deploy DEPLOY_TARGET=local"
	@echo "  make deploy-raspi RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub"

preflight:
ifeq ($(DEPLOY_TARGET),local)
	@$(MAKE_CMD) --no-print-directory preflight-local
else ifeq ($(DEPLOY_TARGET),raspi)
	@$(MAKE_CMD) --no-print-directory preflight-raspi
else
	@echo "ERROR: DEPLOY_TARGET must be local or raspi (received: $(DEPLOY_TARGET))"; exit 2
endif

preflight-local: preflight-host preflight-repo preflight-env preflight-compose preflight-port
	@echo "Local preflight passed."

preflight-raspi: preflight-host-raspi preflight-repo-raspi preflight-env-raspi preflight-compose-raspi
	@echo "Raspberry Pi preflight passed for $(RASPI_HOST)."

preflight-host:
	@command -v docker >/dev/null || { echo "ERROR: Docker is not installed or not on PATH"; exit 1; }
	@docker --version >/dev/null
	@docker compose version >/dev/null

preflight-host-raspi:
	@test -n "$(RASPI_HOST)" || { echo "ERROR: RASPI_HOST is empty"; exit 1; }
	@ssh "$(RASPI_HOST)" 'set -eu; command -v docker >/dev/null; docker --version >/dev/null; docker compose version >/dev/null'

preflight-repo:
	@test -d .git || { echo "ERROR: current directory is not a Git repository"; exit 1; }
	@test -f "$(COMPOSE_FILE)" || { echo "ERROR: missing $(COMPOSE_FILE)"; exit 1; }

preflight-repo-raspi:
	@test -n "$(RASPI_REPO_PATH)" || { echo "ERROR: RASPI_REPO_PATH is empty"; exit 1; }
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; [ -d "$$repo" ] || { echo "ERROR: missing repo path $$repo"; exit 1; }; [ -d "$$repo/.git" ] || { echo "ERROR: $$repo is not a Git repository"; exit 1; }; [ -f "$$repo/$(COMPOSE_FILE)" ] || { echo "ERROR: missing $$repo/$(COMPOSE_FILE)"; exit 1; }'

preflight-env:
	@test -f "$(ENV_FILE)" || { echo "ERROR: missing $(ENV_FILE). Copy .env.example to .env and set the production secret."; exit 1; }

preflight-env-raspi:
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; [ -f "$$repo/$(ENV_FILE)" ] || { echo "ERROR: missing $$repo/$(ENV_FILE). Copy .env.example to .env and set the production secret."; exit 1; }'

preflight-compose:
	@APP_ENV="$(LOCAL_APP_ENV)" docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" config --quiet

preflight-compose-raspi:
	@ssh "$(RASPI_HOST)" 'set -eu; cd "$(RASPI_REPO_PATH)"; APP_ENV="$(DEPLOY_APP_ENV)" docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" config --quiet'

preflight-port:
	@owner="$$(docker ps --filter "publish=$(WEB_PORT)" --format '{{.Names}}' | head -n 1)"; if [ -n "$$owner" ]; then project="$$(docker inspect -f '{{ index .Config.Labels "com.docker.compose.project" }}' "$$owner" 2>/dev/null || true)"; if [ "$$project" != "$(APP_NAME)" ]; then echo "ERROR: port $(WEB_PORT) is used by $$owner (Compose project: $${project:-unknown})"; exit 1; fi; echo "Local web port $(WEB_PORT) is already owned by the $(APP_NAME) stack."; elif command -v ss >/dev/null 2>&1 && ss -ltn | grep -qE "[:.]$(WEB_PORT)[[:space:]]"; then echo "ERROR: port $(WEB_PORT) is already in use"; exit 1; else echo "Local web port $(WEB_PORT) is available."; fi

deploy:
ifeq ($(DEPLOY_TARGET),local)
	@$(MAKE_CMD) --no-print-directory deploy-local
else ifeq ($(DEPLOY_TARGET),raspi)
	@$(MAKE_CMD) --no-print-directory deploy-raspi
else
	@echo "ERROR: DEPLOY_TARGET must be local or raspi (received: $(DEPLOY_TARGET))"; exit 2
endif

deploy-local: preflight-local
	@APP_ENV="$(LOCAL_APP_ENV)" docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" up -d --build --remove-orphans --wait
	@echo "Local stack is running at http://localhost:$(WEB_PORT)"

deploy-raspi: preflight-raspi
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; cd "$$repo"; [ "$$(git rev-parse --abbrev-ref HEAD)" = "$(BRANCH)" ] || { echo "ERROR: branch is not $(BRANCH)"; exit 1; }; dirty="$$(git status --porcelain)"; test -z "$$dirty" || { echo "ERROR: remote working tree is dirty"; printf "%s\n" "$$dirty"; exit 1; }; git pull --ff-only; APP_ENV="$(DEPLOY_APP_ENV)" docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" up -d --build --remove-orphans --wait'
	@echo "Raspberry Pi deployment completed on $(RASPI_HOST)."

local-up: deploy-local

local-down:
	@docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" down

status:
ifeq ($(DEPLOY_TARGET),local)
	@docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" ps
else ifeq ($(DEPLOY_TARGET),raspi)
	@ssh "$(RASPI_HOST)" 'cd "$(RASPI_REPO_PATH)" && docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" ps'
else
	@echo "ERROR: DEPLOY_TARGET must be local or raspi (received: $(DEPLOY_TARGET))"; exit 2
endif

logs-api:
ifeq ($(DEPLOY_TARGET),local)
	@docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" logs -f --tail=200 api
else ifeq ($(DEPLOY_TARGET),raspi)
	@ssh "$(RASPI_HOST)" 'cd "$(RASPI_REPO_PATH)" && docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" logs -f --tail=200 api'
else
	@echo "ERROR: DEPLOY_TARGET must be local or raspi (received: $(DEPLOY_TARGET))"; exit 2
endif

logs-frontend:
ifeq ($(DEPLOY_TARGET),local)
	@docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" logs -f --tail=200 frontend
else ifeq ($(DEPLOY_TARGET),raspi)
	@ssh "$(RASPI_HOST)" 'cd "$(RASPI_REPO_PATH)" && docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" logs -f --tail=200 frontend'
else
	@echo "ERROR: DEPLOY_TARGET must be local or raspi (received: $(DEPLOY_TARGET))"; exit 2
endif
