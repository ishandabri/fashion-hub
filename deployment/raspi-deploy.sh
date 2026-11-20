#!/usr/bin/env bash
set -Eeuo pipefail

repo="$1"
tag="$2"
env_file="$3"
compose_file="$4"
app_name="$5"
app_env="$6"
rollback_mode="$7"

cd "$repo"
state_dir="${XDG_STATE_HOME:-$HOME/.local/state}/fashion-hub"
previous_tag=""
if [ -f "$state_dir/last-healthy-tag" ]; then
  previous_tag="$(cat "$state_dir/last-healthy-tag")"
fi

test -z "$(git status --porcelain)" || { echo "ERROR: remote working tree is dirty"; exit 1; }
git fetch --tags origin
git rev-parse --verify "refs/tags/$tag^{commit}" >/dev/null
test "$(git cat-file -t "refs/tags/$tag")" = tag || { echo "ERROR: release tag must be annotated"; exit 1; }

compose=(docker compose --env-file "$env_file" -f "$compose_file" -p "$app_name")
checkout_release() {
  local release_tag="$1"
  git checkout --detach "$release_tag"
  export APP_VERSION="${release_tag#v}"
  export APP_REVISION="$(git rev-parse --short=12 HEAD)"
  export APP_BUILT_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  export APP_ENV="$app_env"
  "${compose[@]}" config --quiet
}

checkout_release "$tag"
if ! "${compose[@]}" build; then
  echo "ERROR: release image build failed; running containers were not replaced."
  exit 1
fi

if "${compose[@]}" up -d --no-build --remove-orphans --wait; then
  mkdir -p "$state_dir"
  printf '%s\n' "$tag" > "$state_dir/.last-healthy-tag.$$"
  mv "$state_dir/.last-healthy-tag.$$" "$state_dir/last-healthy-tag"
  current_api="fashion-hub-api:${APP_VERSION}-${APP_REVISION}"
  current_frontend="fashion-hub-frontend:${APP_VERSION}-${APP_REVISION}"
  previous_api=""
  previous_frontend=""
  if [ -n "$previous_tag" ] && git rev-parse --verify "refs/tags/$previous_tag^{commit}" >/dev/null 2>&1; then
    previous_api="fashion-hub-api:${previous_tag#v}-$(git rev-parse --short=12 "$previous_tag^{commit}")"
    previous_frontend="fashion-hub-frontend:${previous_tag#v}-$(git rev-parse --short=12 "$previous_tag^{commit}")"
  fi
  for image in $(docker image ls --format '{{.Repository}}:{{.Tag}}' | grep -E '^fashion-hub-(api|frontend):[^:]+-[0-9a-f]+$' || true); do
    [ "$image" = "$current_api" ] || [ "$image" = "$current_frontend" ] || [ "$image" = "$previous_api" ] || [ "$image" = "$previous_frontend" ] || docker image rm "$image" >/dev/null 2>&1 || true
  done
  echo "Deployed $tag at $APP_REVISION."
  exit 0
fi

echo "ERROR: release $tag failed health checks."
[ "$rollback_mode" = 1 ] && echo "WARNING: explicit rollback requested; migration compatibility is the operator's responsibility."
[ -n "$previous_tag" ] || { echo "ERROR: no valid last healthy tag is available for rollback."; exit 1; }
git rev-parse --verify "refs/tags/$previous_tag^{commit}" >/dev/null 2>&1 || { echo "ERROR: last healthy tag is invalid."; exit 1; }
if ! git diff --quiet "$previous_tag" "$tag" -- backend/migrations; then
  echo "ERROR: migration files changed; automatic rollback skipped."
  exit 1
fi

echo "Attempting automatic rollback to $previous_tag."
checkout_release "$previous_tag"
"${compose[@]}" build
"${compose[@]}" up -d --no-build --remove-orphans --wait || { echo "ERROR: automatic rollback failed."; exit 1; }
echo "Automatic rollback to $previous_tag completed; requested release failed."
exit 1
