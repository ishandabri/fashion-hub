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
RELEASE_TAG ?=
ROLLBACK_MODE ?= 0
COMPOSE_FILE ?= docker-compose.yml
ENV_FILE ?= .env
WEB_PORT ?= 6001
DEPLOY_TARGET ?= raspi
MAKE_CMD ?= make
LOCAL_APP_ENV ?= development
DEPLOY_APP_ENV ?= production

RASPI_HOST ?= raspi
RASPI_REPO_PATH ?= /home/ishan/projects/fashion-hub

.PHONY: help preflight preflight-local preflight-raspi preflight-host preflight-repo preflight-env preflight-compose preflight-port preflight-release deploy deploy-local deploy-raspi rollback local-up local-down status logs-api logs-frontend

help:
	@echo "Available targets:"
	@echo "  preflight         Validate the selected target (DEPLOY_TARGET=local|raspi)."
	@echo "  deploy            Preflight and deploy the selected target (DEPLOY_TARGET=local|raspi)."
	@echo "  preflight-local   Validate Docker, .env, Compose, and the local web port."
	@echo "  deploy-local      Build and start the local Docker stack."
	@echo "  preflight-raspi   Validate SSH, Docker, remote repo, release tag, .env, and Compose."
	@echo "  deploy-raspi      Deploy a tagged release and build/start the stack on the Raspberry Pi."
	@echo "  rollback          Deploy a tagged release explicitly as a rollback."
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
	@echo "  make deploy-raspi RELEASE_TAG=v0.1.1 RASPI_HOST=raspi RASPI_REPO_PATH=/home/ishan/projects/fashion-hub"

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

preflight-raspi: preflight-host-raspi preflight-repo-raspi preflight-env-raspi preflight-compose-raspi preflight-release
	@echo "Raspberry Pi preflight passed for $(RASPI_HOST) and $(RELEASE_TAG)."

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

preflight-release:
	@set -eu; tag="$(RELEASE_TAG)"; test -n "$$tag" || { echo "ERROR: RELEASE_TAG is required, for example RELEASE_TAG=v0.1.1"; exit 1; }; printf '%s\n' "$$tag" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$$' || { echo "ERROR: RELEASE_TAG must use SemVer tag format vMAJOR.MINOR.PATCH"; exit 1; }; git rev-parse --verify "refs/tags/$$tag^{commit}" >/dev/null || { echo "ERROR: local Git tag $$tag does not exist"; exit 1; }; test "$$(git cat-file -t "refs/tags/$$tag")" = tag || { echo "ERROR: $$tag must be an annotated Git tag"; exit 1; }; test -z "$$(git status --porcelain)" || { echo "ERROR: local working tree is dirty"; exit 1; }; version="$${tag#v}"; frontend_version="$$(node -p "require('./frontend/package.json').version")"; backend_version="$$(python -c "import tomllib; print(tomllib.load(open('backend/pyproject.toml','rb'))['project']['version'])")"; test "$$frontend_version" = "$$version" || { echo "ERROR: frontend package version $$frontend_version does not match $$version"; exit 1; }; test "$$backend_version" = "$$version" || { echo "ERROR: backend package version $$backend_version does not match $$version"; exit 1; }

preflight-env:
	@test -f "$(ENV_FILE)" || { echo "ERROR: missing $(ENV_FILE). Copy .env.example to .env and set the production secret."; exit 1; }

preflight-env-raspi:
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; [ -f "$$repo/$(ENV_FILE)" ] || { echo "ERROR: missing $$repo/$(ENV_FILE). Copy .env.example to .env and set the production secret."; exit 1; }'

preflight-compose:
	@APP_ENV="$(LOCAL_APP_ENV)" docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" config --quiet

preflight-compose-raspi:
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; cd "$$repo"; tag="$(RELEASE_TAG)"; git fetch --tags origin; git rev-parse --verify "refs/tags/$$tag^{commit}" >/dev/null || { echo "ERROR: remote Git tag $$tag does not exist"; exit 1; }; test "$$(git cat-file -t "refs/tags/$$tag")" = tag || { echo "ERROR: remote tag $$tag must be annotated"; exit 1; }; tmp="$$(mktemp -d)"; trap "rm -rf $$tmp" EXIT; git archive "$$tag" | tar -x -C "$$tmp"; APP_ENV="$(DEPLOY_APP_ENV)" docker compose --env-file "$$repo/$(ENV_FILE)" -f "$$tmp/$(COMPOSE_FILE)" config --quiet'

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
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; cd "$$repo"; tag="$(RELEASE_TAG)"; state_dir="$${XDG_STATE_HOME:-$$HOME/.local/state}/fashion-hub"; previous_tag=""; [ -f "$$state_dir/last-healthy-tag" ] && previous_tag="$$(cat "$$state_dir/last-healthy-tag")" || true; dirty="$$(git status --porcelain)"; test -z "$$dirty" || { echo "ERROR: remote working tree is dirty"; printf "%s\n" "$$dirty"; exit 1; }; git fetch --tags origin; git rev-parse --verify "refs/tags/$$tag^{commit}" >/dev/null || { echo "ERROR: remote Git tag $$tag does not exist"; exit 1; }; test "$$(git cat-file -t "refs/tags/$$tag")" = tag || { echo "ERROR: remote tag $$tag must be annotated"; exit 1; }; git checkout --detach "$$tag"; export APP_VERSION="$${tag#v}" APP_REVISION="$$(git rev-parse --short=12 HEAD)" APP_BUILT_AT="$$(date -u +%Y-%m-%dT%H:%M:%SZ)" APP_ENV="$(DEPLOY_APP_ENV)"; docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" config --quiet; if ! docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" build; then echo "ERROR: release image build failed; running containers were not replaced."; exit 1; fi; if docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" up -d --no-build --remove-orphans --wait; then mkdir -p "$$state_dir"; tmp="$$state_dir/.last-healthy-tag.$$$$"; printf "%s\n" "$$tag" > "$$tmp"; mv "$$tmp" "$$state_dir/last-healthy-tag"; echo "Deployed $$tag at $$(git rev-parse --short=12 HEAD)."; exit 0; fi; echo "ERROR: release $$tag failed health checks."; if [ "$(ROLLBACK_MODE)" = "1" ]; then echo "WARNING: explicit rollback requested; migration compatibility is the operator's responsibility."; fi; if [ -z "$$previous_tag" ] || ! git rev-parse --verify "refs/tags/$$previous_tag^{commit}" >/dev/null 2>&1; then echo "ERROR: no valid last healthy tag is available for rollback."; exit 1; fi; if ! git diff --quiet "$$previous_tag" "$$tag" -- backend/migrations; then echo "ERROR: migration files changed; automatic rollback skipped."; exit 1; fi; echo "Attempting automatic rollback to $$previous_tag."; git checkout --detach "$$previous_tag"; export APP_VERSION="$${previous_tag#v}" APP_REVISION="$$(git rev-parse --short=12 HEAD)" APP_BUILT_AT="$$(date -u +%Y-%m-%dT%H:%M:%SZ)"; if ! docker image inspect "fashion-hub-api:$$APP_VERSION-$$APP_REVISION" >/dev/null 2>&1 || ! docker image inspect "fashion-hub-frontend:$$APP_VERSION-$$APP_REVISION" >/dev/null 2>&1; then docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" build; fi; if ! docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" up -d --no-build --remove-orphans --wait; then echo "ERROR: automatic rollback to $$previous_tag failed."; exit 1; fi; echo "Automatic rollback to $$previous_tag completed; requested release failed."; exit 1'
	@echo "Raspberry Pi deployment completed on $(RASPI_HOST) for $(RELEASE_TAG)."

rollback: ROLLBACK_MODE=1
rollback: deploy-raspi

local-up: deploy-local

local-down:
	@docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" down

status:
ifeq ($(DEPLOY_TARGET),local)
	@docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" ps
else ifeq ($(DEPLOY_TARGET),raspi)
	@ssh "$(RASPI_HOST)" 'set -eu; repo="$(RASPI_REPO_PATH)"; cd "$$repo"; echo "Repository release: $$(git describe --tags --exact-match 2>/dev/null || echo unknown) at $$(git rev-parse --short=12 HEAD)"; docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" ps; docker compose --env-file "$(ENV_FILE)" -f "$(COMPOSE_FILE)" -p "$(APP_NAME)" exec -T api sh -c "printf \"API release: %s (%s)\\n\" \"\$$APP_VERSION\" \"\$$APP_REVISION\""'
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
