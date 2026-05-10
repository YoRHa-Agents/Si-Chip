#!/usr/bin/env bash
# Si-Chip installer
#   Installs the Si-Chip Skill payload (SKILL.md + DESIGN.md + 19 references
#   + 5 scripts = 26 files at v0.5.2) into a Cursor and/or Claude Code
#   skills directory (global or repo scope), and/or the Codex BRIDGE
#   profile (2 files: .codex/profiles/si-chip.md +
#   .codex/instructions/si-chip-bridge.md).
#
#   Source of truth: https://github.com/YoRHa-Agents/Si-Chip
#   Spec:            .local/research/spec_v0.5.0.md (FROZEN; v0.5.1 patch
#                    operationalizes Codex bridge install per §7.2; v0.5.2
#                    install hotfix backfills v0.5.1 tarball + adds
#                    --strip-components=1 to fix HTTP-extract nesting bug;
#                    v0.1.0..v0.4.7 retained as pinned historical snapshots)
#
#   Per spec §7.2 + §11.2, supported install targets at v0.5.2 are:
#     * Cursor       — full SKILL tree at `.cursor/skills/si-chip/`
#     * Claude Code  — full SKILL tree at `.claude/skills/si-chip/`
#     * Codex        — BRIDGE ONLY: two files under `.codex/{profiles,instructions}/`
#                      pointing back to AGENTS.md (the compiled rule corpus).
#                      Codex native SKILL.md runtime is §11.2 deferred —
#                      gate is v3_strict 2-round pass (current state at
#                      v0.5.0 ship: only v2_tightened achieved 9 times).
#
#   Targets explicitly NOT supported (forever-out per §11.1 / deferred per §11.2):
#     * Copilot CLI / OpenCode / Gemini CLI / generic IDE compat layer.
#     The installer rejects these with a clear pointer to the spec clauses.
#
# SI_CHIP_INSTALLER_STEPS=1
#   Self-reported user-facing step count for the canonical non-interactive
#   one-line flow: `curl -fsSL .../install.sh | bash -s -- --target ...
#   --scope ... --yes`. Parsed by tools/install_telemetry.count_setup_steps
#   (Round 6 dogfood D5 U3 fill). The interactive flow (no --yes, TTY
#   present) prompts for `--target` and `--scope`, adding 2 steps; the
#   headline flow promoted in INSTALL.md / docs/_install_body.md / CHANGELOG
#   v0.1.1 is the non-interactive one-liner which is unambiguously 1 step.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SI_CHIP_VERSION_DEFAULT="v0.5.2"
SOURCE_URL_DEFAULT="https://yorha-agents.github.io/Si-Chip"

# Cursor / Claude SKILL-tree manifest (v0.5.2: 19 references + 5 scripts).
# Order is alphabetic within each subgroup so the file:// loop is stable.
MANIFEST=(
  "SKILL.md"
  "DESIGN.md"
  "references/basic-ability-profile.md"
  "references/core-goal-invariant-r11-summary.md"
  "references/description-discipline-r13-summary.md"
  "references/eval-pack-curation-r12-summary.md"
  "references/half-retirement-r9-summary.md"
  "references/health-smoke-check-r12-summary.md"
  "references/lifecycle-category-r13-summary.md"
  "references/lifecycle-state-machine-r12-summary.md"
  "references/meta-routing-pattern-r13-summary.md"
  "references/method-tagged-metrics-r12-summary.md"
  "references/metrics-r6-summary.md"
  "references/multi-ability-layout-r11-summary.md"
  "references/progressive-disclosure-r13-summary.md"
  "references/real-data-verification-r12-summary.md"
  "references/round-kind-r11-summary.md"
  "references/router-test-r8-summary.md"
  "references/self-dogfood-protocol.md"
  "references/standardized-sections-r13-summary.md"
  "references/token-tier-invariant-r12-summary.md"
  "scripts/profile_static.py"
  "scripts/count_tokens.py"
  "scripts/aggregate_eval.py"
  "scripts/eval_skill_quickstart.md"
  "scripts/real_llm_runner_quickstart.md"
)

EXPECTED_REFS=19
EXPECTED_SCRIPTS=5

# Codex bridge manifest (v0.5.2 bridge-only; per spec §7.2 priority 3).
# Layout is intentionally NOT `.codex/skills/si-chip/SKILL.md` because that
# would imply native SKILL.md runtime (§11.2 deferred). Instead, two
# bridge files live alongside (not inside) any skills/ directory.
CODEX_BRIDGE_MANIFEST=(
  ".codex/profiles/si-chip.md"
  ".codex/instructions/si-chip-bridge.md"
)

EXPECTED_CODEX_BRIDGE_FILES=2

# Tools / IDEs that are EXPLICITLY out-of-scope for the installer.
# Any --target value matching one of these triggers a hard rejection
# with a pointer to the relevant spec clause.
DEFERRED_TARGETS=(
  "copilot"      # §11.2 deferred (generic IDE chase)
  "opencode"     # §11.2 deferred
  "gemini"       # §11.2 deferred
  "gemini-cli"   # §11.2 deferred
  "windsurf"     # §11.1 generic IDE compat layer (forever-out per §11.1 item 3)
  "all-tools"    # ambiguous; users should use --target all (=cursor+claude+codex)
)

# ---------------------------------------------------------------------------
# Globals (populated by parse_args)
# ---------------------------------------------------------------------------

TARGET=""
SCOPE=""
REPO_ROOT=""
SI_CHIP_VERSION="${SI_CHIP_VERSION_DEFAULT}"
SOURCE_URL="${SOURCE_URL_DEFAULT}"
ASSUME_YES=0
DRY_RUN=0
FORCE=0
UNINSTALL=0

TMPDIR_ROOT=""

# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------

log() {
  printf '%s\n' "$*"
}

err() {
  printf 'ERROR: %s\n' "$*" >&2
}

die() {
  err "$*"
  exit 1
}

run() {
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] $*"
  else
    "$@"
  fi
}

cleanup() {
  if [[ -n "${TMPDIR_ROOT}" && -d "${TMPDIR_ROOT}" ]]; then
    rm -rf "${TMPDIR_ROOT}"
  fi
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Banner / help / version
# ---------------------------------------------------------------------------

print_banner() {
  log "// SI-CHIP INSTALLER / ${SI_CHIP_VERSION}"
  log "// YORHA AGENTS / GLORY TO MANKIND"
  log ""
}

print_version_info() {
  log "Si-Chip installer ${SI_CHIP_VERSION_DEFAULT}"
  log "Default source URL: ${SOURCE_URL_DEFAULT}"
}

print_help() {
  cat <<'EOF'
Si-Chip installer v0.5.2

Usage:
  curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash
  curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- --target cursor --scope global --yes
  ./install.sh --target codex --scope repo --repo-root /path/to/myproject --yes
  ./install.sh --target all   --scope global --yes

Flags:
  --target cursor|claude|codex|both|all
                                 Which platform to install for.
                                   cursor / claude  install full SKILL tree.
                                   codex            installs the BRIDGE files
                                                    only (per spec §7.2 +
                                                    §11.2; native SKILL.md
                                                    runtime deferred).
                                   both             = cursor + claude
                                                    (back-compat alias).
                                   all              = cursor + claude + codex.
  --scope global|repo            Where to install
  --repo-root <path>             Repo root (required for --scope repo)
  --version <tag>                Si-Chip version to install (default: v0.5.2)
  --source-url <url>             Override download base (default: pages URL)
  --yes, -y                      Non-interactive
  --dry-run                      Print actions without writing
  --force                        Overwrite existing install without prompting
  --uninstall                    Remove the installed dir for chosen target/scope
  --help, -h                     This help
  --version-info                 Print installer version

Examples:
  # Install all three supported targets globally (Cursor + Claude + Codex bridge)
  ./install.sh --target all --scope global --yes

  # Install Cursor only into a specific repo
  ./install.sh --target cursor --scope repo --repo-root ~/code/myrepo --yes

  # Install just the Codex bridge into a repo (does NOT install SKILL.md tree;
  # spec §11.2 — Codex native SKILL.md runtime is deferred until v3_strict
  # is achieved twice in a row).
  ./install.sh --target codex --scope repo --repo-root ~/code/myrepo --yes

  # Dry-run interactive install
  ./install.sh --dry-run

  # Uninstall from global Claude Code
  ./install.sh --target claude --scope global --uninstall --yes

  # Uninstall the Codex bridge from a repo
  ./install.sh --target codex --scope repo --repo-root ~/code/myrepo --uninstall --yes

Out-of-scope targets (the installer REJECTS these on purpose):
  Copilot CLI / OpenCode / Gemini CLI / Windsurf / generic IDE compat layer.
  Rationale: spec §11.1 item 3 (generic IDE compat = forever-out) and
  §11.2 (broader IDE support is deferred and gated on v3_strict 2-round
  pass; v0.5.0 ship achieved only v2_tightened 9 times).

Payload delivery:
  Cursor / Claude SKILL tree (HTTP path):
    The installer downloads a single tarball at
      <source-url>/skills/si-chip-<version>.tar.gz
    and extracts it into the target install directory.
  Codex bridge (HTTP path):
    The installer fetches each bridge file individually from
      <source-url>/codex/profiles/si-chip.md
      <source-url>/codex/instructions/si-chip-bridge.md
    (no tarball — only 2 small markdown files).
  Over file:// the installer copies each manifest entry directly from the
  source tree, including the bridge files at <source-url>/.codex/...

Si-Chip is governed by the spec at:
  https://github.com/YoRHa-Agents/Si-Chip/blob/main/.local/research/spec_v0.5.0.md
EOF
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

require_value() {
  # require_value <flag-name> <value>
  if [[ -z "${2:-}" || "${2:0:1}" == "-" ]]; then
    die "flag $1 requires a value"
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --target)
        require_value "$1" "${2:-}"
        TARGET="$2"
        shift 2
        ;;
      --scope)
        require_value "$1" "${2:-}"
        SCOPE="$2"
        shift 2
        ;;
      --repo-root)
        require_value "$1" "${2:-}"
        REPO_ROOT="$2"
        shift 2
        ;;
      --version)
        require_value "$1" "${2:-}"
        SI_CHIP_VERSION="$2"
        shift 2
        ;;
      --source-url)
        require_value "$1" "${2:-}"
        SOURCE_URL="$2"
        shift 2
        ;;
      --yes|-y)
        ASSUME_YES=1
        shift
        ;;
      --dry-run)
        DRY_RUN=1
        shift
        ;;
      --force)
        FORCE=1
        shift
        ;;
      --uninstall)
        UNINSTALL=1
        shift
        ;;
      --help|-h)
        print_help
        exit 0
        ;;
      --version-info)
        print_version_info
        exit 0
        ;;
      *)
        err "unknown argument: $1"
        log ""
        print_help
        exit 2
        ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Validation + interactive prompts
# ---------------------------------------------------------------------------

is_tty() {
  [[ -t 0 && -t 1 ]]
}

is_deferred_target() {
  # is_deferred_target <value> — returns 0 if the value matches a
  # spec-§11.x out-of-scope target, 1 otherwise.
  local needle="$1"
  local t
  for t in "${DEFERRED_TARGETS[@]}"; do
    if [[ "${needle}" == "${t}" ]]; then
      return 0
    fi
  done
  return 1
}

reject_deferred_target() {
  # reject_deferred_target <value>
  local value="$1"
  err "--target ${value} is NOT supported by the Si-Chip installer."
  err ""
  err "Si-Chip spec §11.1 (forever-out) and §11.2 (deferred) explicitly"
  err "restrict the install surface. Allowed --target values are:"
  err "  cursor / claude / codex / both / all"
  err ""
  err "Codex is supported as BRIDGE ONLY (see --target codex; spec §7.2)."
  err "Generic IDE / Agent runtime compat layers (Copilot CLI, OpenCode,"
  err "Gemini CLI, Windsurf, ...) are §11.1 forever-out OR §11.2 deferred"
  err "until the spec is bumped past v0.x AND v3_strict passes 2 rounds."
  err ""
  err "If you really need one of these surfaces, file an issue at:"
  err "  https://github.com/YoRHa-Agents/Si-Chip/issues"
  exit 2
}

prompt_target() {
  local choice
  log "Select target platform:"
  log "  1) Cursor"
  log "  2) Claude Code"
  log "  3) Codex (bridge only, per spec §7.2)"
  log "  4) Both Cursor + Claude Code"
  log "  5) All three (Cursor + Claude + Codex bridge)"
  printf 'Choice [1]: '
  read -r choice || true
  case "${choice:-1}" in
    1|"") TARGET="cursor" ;;
    2)    TARGET="claude" ;;
    3)    TARGET="codex"  ;;
    4)    TARGET="both"   ;;
    5)    TARGET="all"    ;;
    *)    die "invalid choice: ${choice}" ;;
  esac
}

prompt_scope() {
  local choice
  log "Select install scope:"
  log "  1) Global (~/.<platform>/skills/si-chip ; ~/.codex/{profiles,instructions}/si-chip*)"
  log "  2) Repo  (<repo>/.<platform>/skills/si-chip ; <repo>/.codex/{profiles,instructions}/si-chip*)"
  printf 'Choice [1]: '
  read -r choice || true
  case "${choice:-1}" in
    1|"") SCOPE="global" ;;
    2)    SCOPE="repo" ;;
    *)    die "invalid choice: ${choice}" ;;
  esac
}

prompt_repo_root() {
  local default_root="${PWD}"
  local choice
  printf 'Repo root [%s]: ' "${default_root}"
  read -r choice || true
  REPO_ROOT="${choice:-${default_root}}"
}

resolve_inputs() {
  # Reject deferred / forever-out targets BEFORE the allow-list check so
  # the user gets the spec-pointer rejection message (not the generic
  # "must be one of" message).
  if [[ -n "${TARGET}" ]] && is_deferred_target "${TARGET}"; then
    reject_deferred_target "${TARGET}"
  fi

  if [[ -n "${TARGET}" \
        && "${TARGET}" != "cursor" \
        && "${TARGET}" != "claude" \
        && "${TARGET}" != "codex"  \
        && "${TARGET}" != "both"   \
        && "${TARGET}" != "all" ]]; then
    die "--target must be one of: cursor | claude | codex | both | all (got: ${TARGET})"
  fi
  if [[ -n "${SCOPE}" && "${SCOPE}" != "global" && "${SCOPE}" != "repo" ]]; then
    die "--scope must be one of: global | repo (got: ${SCOPE})"
  fi

  if [[ -z "${TARGET}" ]]; then
    if [[ "${ASSUME_YES}" -eq 1 ]]; then
      die "--target is required when --yes is set"
    fi
    if ! is_tty; then
      die "--target is required (no TTY for interactive prompt)"
    fi
    prompt_target
  fi

  if [[ -z "${SCOPE}" ]]; then
    if [[ "${ASSUME_YES}" -eq 1 ]]; then
      die "--scope is required when --yes is set"
    fi
    if ! is_tty; then
      die "--scope is required (no TTY for interactive prompt)"
    fi
    prompt_scope
  fi

  if [[ "${SCOPE}" == "repo" && -z "${REPO_ROOT}" ]]; then
    if [[ "${ASSUME_YES}" -eq 1 ]]; then
      REPO_ROOT="${PWD}"
    elif is_tty; then
      prompt_repo_root
    else
      die "--repo-root is required when --scope repo and no TTY available"
    fi
  fi

  if [[ "${SCOPE}" == "repo" ]]; then
    if [[ ! -d "${REPO_ROOT}" ]]; then
      die "repo root does not exist: ${REPO_ROOT}"
    fi
    REPO_ROOT="$(cd "${REPO_ROOT}" && pwd)"
  fi
}

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

install_dir_for() {
  # install_dir_for <platform>  -> echoes absolute path
  #   cursor / claude  -> <scope>/.<platform>/skills/si-chip
  #   codex            -> <scope>/.codex
  # Codex returns a SHALLOW path because the bridge files live at
  # `.codex/profiles/...` and `.codex/instructions/...`, NOT inside a
  # `skills/si-chip/` subdir (which would imply native runtime).
  local platform="$1"
  local sub
  case "${platform}" in
    cursor) sub=".cursor" ;;
    claude) sub=".claude" ;;
    codex)  sub=".codex"  ;;
    *) die "internal: unknown platform ${platform}" ;;
  esac

  local base
  if [[ "${SCOPE}" == "global" ]]; then
    if [[ -z "${HOME:-}" ]]; then
      die "HOME is not set; cannot resolve global install dir"
    fi
    base="${HOME}/${sub}"
  else
    base="${REPO_ROOT}/${sub}"
  fi

  if [[ "${platform}" == "codex" ]]; then
    printf '%s\n' "${base}"
  else
    printf '%s/skills/si-chip\n' "${base}"
  fi
}

platforms_for_target() {
  case "${TARGET}" in
    cursor) printf 'cursor\n' ;;
    claude) printf 'claude\n' ;;
    codex)  printf 'codex\n'  ;;
    both)   printf 'cursor\nclaude\n' ;;
    all)    printf 'cursor\nclaude\ncodex\n' ;;
    *) die "internal: unknown target ${TARGET}" ;;
  esac
}

# ---------------------------------------------------------------------------
# Pre-flight
# ---------------------------------------------------------------------------

check_bash_version() {
  if [[ -z "${BASH_VERSINFO:-}" ]]; then
    log "WARN: cannot detect bash version; continuing"
    return 0
  fi
  if (( BASH_VERSINFO[0] < 4 )); then
    log "WARN: bash ${BASH_VERSION} is older than 4.0; some features may not work"
  fi
}

is_file_url() {
  [[ "${SOURCE_URL}" == file://* ]]
}

is_http_url() {
  [[ "${SOURCE_URL}" == http://* || "${SOURCE_URL}" == https://* ]]
}

check_curl() {
  if is_http_url; then
    if ! command -v curl >/dev/null 2>&1; then
      die "curl is required for http(s) sources but was not found. Install curl and re-run."
    fi
  fi
}

check_writable_parent() {
  # check_writable_parent <install_dir>
  local install_dir="$1"
  local parent
  parent="$(dirname "${install_dir}")"
  if [[ ! -d "${parent}" ]]; then
    return 0
  fi
  if [[ ! -w "${parent}" ]]; then
    die "parent directory is not writable: ${parent}"
  fi
}

confirm_overwrite() {
  # confirm_overwrite <install_dir> <sentinel_relpath>
  # Skill-tree platforms use SKILL.md as sentinel; codex bridge uses its
  # profile file. We pass the sentinel from the caller so this helper
  # works for both layouts.
  local install_dir="$1"
  local sentinel="${2:-SKILL.md}"
  if [[ ! -d "${install_dir}" ]]; then
    return 0
  fi
  if [[ ! -f "${install_dir}/${sentinel}" ]]; then
    return 0
  fi
  if [[ "${FORCE}" -eq 1 || "${ASSUME_YES}" -eq 1 ]]; then
    log "Overwriting existing install at ${install_dir}"
    return 0
  fi
  if ! is_tty; then
    die "existing install at ${install_dir}; pass --force to overwrite"
  fi
  local ans
  printf 'Existing Si-Chip install found at %s. Overwrite? [y/N]: ' "${install_dir}"
  read -r ans || true
  case "${ans}" in
    y|Y|yes|YES) return 0 ;;
    *) die "aborted by user" ;;
  esac
}

# ---------------------------------------------------------------------------
# Fetch / install / uninstall
# ---------------------------------------------------------------------------

tarball_basename() {
  printf 'si-chip-%s.tar.gz\n' "${SI_CHIP_VERSION#v}"
}

fetch_one() {
  # fetch_one <relpath> <dst-abs>  (file:// path only)
  # SKILL-tree files live in TWO layouts depending on what --source-url
  # points at:
  #   1. Extracted-tarball:    <base>/skills/si-chip/...     (original layout)
  #   2. Repo source-of-truth: <base>/.agents/skills/si-chip/... (per spec §7.2)
  # We try the canonical extracted-tarball layout first (back-compat with
  # all v0.1.0..v0.5.0 dogfood logs), then fall back to the repo SoT layout
  # so file:// installs work directly against a checked-out repo.
  local rel="$1"
  local dst="$2"
  local base="${SOURCE_URL#file://}"
  local src=""
  local candidate
  for candidate in \
      "${base}/skills/si-chip/${rel}" \
      "${base}/.agents/skills/si-chip/${rel}"; do
    if [[ -f "${candidate}" ]]; then
      src="${candidate}"
      break
    fi
  done
  if [[ -z "${src}" ]]; then
    die "missing source file: tried ${base}/skills/si-chip/${rel} and ${base}/.agents/skills/si-chip/${rel}"
  fi
  run mkdir -p "$(dirname "${dst}")"
  run cp "${src}" "${dst}"
}

fetch_one_url() {
  # fetch_one_url <relpath-under-source-url> <dst-abs>  (http(s) path only)
  local rel="$1"
  local dst="$2"
  local url="${SOURCE_URL%/}/${rel}"
  run mkdir -p "$(dirname "${dst}")"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] curl -fsSL ${url} -o ${dst}"
    return 0
  fi
  if ! curl -fsSL "${url}" -o "${dst}"; then
    die "failed to download ${url}"
  fi
}

stage_payload_file() {
  # stage_payload_file <staging-dir>
  local staging="$1"
  local rel
  for rel in "${MANIFEST[@]}"; do
    fetch_one "${rel}" "${staging}/${rel}"
  done
}

stage_payload_http() {
  # stage_payload_http <staging-dir>
  local staging="$1"
  local tarball_name tarball_url tarball_path
  tarball_name="$(tarball_basename)"
  tarball_url="${SOURCE_URL%/}/skills/${tarball_name}"
  tarball_path="${TMPDIR_ROOT}/${tarball_name}"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] curl -fsSL ${tarball_url} -o ${tarball_path}"
    log "[dry-run] verify gzip magic of ${tarball_path}"
    log "[dry-run] mkdir -p ${staging}"
    log "[dry-run] tar -xzf ${tarball_path} -C ${staging}"
    return 0
  fi

  if ! curl -fsSL "${tarball_url}" -o "${tarball_path}"; then
    die "failed to download ${tarball_url}"
  fi
  if ! gzip -t "${tarball_path}" >/dev/null 2>&1; then
    local diag="unknown"
    if command -v file >/dev/null 2>&1; then
      diag="$(file -b "${tarball_path}")"
    fi
    die "downloaded payload is not a valid gzip file (got: ${diag}) from ${tarball_url}"
  fi
  mkdir -p "${staging}"
  # `--strip-components=1` peels the canonical `si-chip/` top-level dir
  # off the tarball entries (every v0.1.0..v0.5.x tarball wraps the
  # payload in a single `si-chip/` dir; see CHANGELOG entry per-release
  # `tar --sort=name ... -czf docs/skills/si-chip-X.Y.Z.tar.gz si-chip/`).
  # Without --strip-components the verifier finds SKILL.md at
  # `<install_dir>/si-chip/SKILL.md` instead of `<install_dir>/SKILL.md`
  # and dies with "post-install: SKILL.md missing" — the historical HTTP
  # install bug fixed in v0.5.2.
  if ! tar -xzf "${tarball_path}" -C "${staging}" --strip-components=1; then
    die "failed to extract ${tarball_name}"
  fi
}

stage_payload() {
  # stage_payload <staging-dir>
  local staging="$1"
  if is_file_url; then
    stage_payload_file "${staging}"
  elif is_http_url; then
    stage_payload_http "${staging}"
  else
    die "unsupported --source-url scheme: ${SOURCE_URL} (expected http://, https://, or file://)"
  fi
}

# Codex-bridge file fetch — file:// path. Bridge files live in TWO
# layouts depending on the source root:
#   1. Repo root layout:  <base>/.codex/{profiles,instructions}/...
#   2. Docs/Pages mirror: <base>/codex/{profiles,instructions}/...
# We try repo-root first (the primary source-of-truth layout) and fall
# back to the docs/Pages mirror so the same installer code works whether
# the user points --source-url at the repo or at the docs/ tree.
fetch_codex_bridge_file() {
  # fetch_codex_bridge_file <relpath-after-codex-root> <dst-abs>
  # Example: fetch_codex_bridge_file "profiles/si-chip.md" "$out"
  local rel="$1"
  local dst="$2"
  local base="${SOURCE_URL#file://}"
  local src=""
  local candidate
  for candidate in "${base}/.codex/${rel}" "${base}/codex/${rel}"; do
    if [[ -f "${candidate}" ]]; then
      src="${candidate}"
      break
    fi
  done
  if [[ -z "${src}" ]]; then
    die "missing codex bridge source file: tried ${base}/.codex/${rel} and ${base}/codex/${rel}"
  fi
  run mkdir -p "$(dirname "${dst}")"
  run cp "${src}" "${dst}"
}

# Codex-bridge file fetch — http(s) path. Bridge files are served from
# `<source-url>/codex/{profiles,instructions}/...` (mirrored into
# `docs/codex/...` for the GitHub Pages root). NOT a tarball.
fetch_codex_bridge_http() {
  # fetch_codex_bridge_http <relpath-after-codex-root> <dst-abs>
  # Example: fetch_codex_bridge_http "profiles/si-chip.md" "$out"
  local rel="$1"
  local dst="$2"
  fetch_one_url "codex/${rel}" "${dst}"
}

verify_install() {
  # verify_install <install_dir>
  local install_dir="$1"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] verify ${install_dir} (skipped)"
    return 0
  fi
  if [[ ! -f "${install_dir}/SKILL.md" ]]; then
    die "post-install: SKILL.md missing at ${install_dir}"
  fi
  local ref_count script_count
  ref_count=$(ls "${install_dir}/references" 2>/dev/null | wc -l | tr -d ' ')
  script_count=$(ls "${install_dir}/scripts" 2>/dev/null | wc -l | tr -d ' ')
  if [[ "${ref_count}" != "${EXPECTED_REFS}" ]]; then
    die "post-install: expected ${EXPECTED_REFS} reference files, found ${ref_count} at ${install_dir}/references"
  fi
  if [[ "${script_count}" != "${EXPECTED_SCRIPTS}" ]]; then
    die "post-install: expected ${EXPECTED_SCRIPTS} script files, found ${script_count} at ${install_dir}/scripts"
  fi
}

verify_codex_bridge_install() {
  # verify_codex_bridge_install <codex_dir>  ($codex_dir = $HOME/.codex or <repo>/.codex)
  local codex_dir="$1"
  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] verify codex bridge ${codex_dir} (skipped)"
    return 0
  fi
  local missing=0
  local rel
  for rel in "profiles/si-chip.md" "instructions/si-chip-bridge.md"; do
    if [[ ! -f "${codex_dir}/${rel}" ]]; then
      err "post-install: codex bridge file missing: ${codex_dir}/${rel}"
      missing=1
    fi
  done
  if [[ "${missing}" -ne 0 ]]; then
    die "codex bridge install verification failed"
  fi
}

install_skill_tree_one() {
  # install_skill_tree_one <platform>  (cursor | claude only)
  local platform="$1"
  local install_dir
  install_dir="$(install_dir_for "${platform}")"

  log ""
  log "=> Installing Si-Chip (${platform}) to ${install_dir}"

  check_writable_parent "${install_dir}"
  confirm_overwrite "${install_dir}" "SKILL.md"

  local staging="${install_dir}.new"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] stage payload to ${staging}"
    log "[dry-run] rm -rf ${install_dir}"
    log "[dry-run] mv ${staging} ${install_dir}"
  else
    if [[ -e "${staging}" ]]; then
      rm -rf "${staging}"
    fi
    mkdir -p "${staging}"
  fi

  stage_payload "${staging}"

  if [[ "${DRY_RUN}" -eq 0 ]]; then
    if [[ -d "${install_dir}" ]]; then
      rm -rf "${install_dir}"
    fi
    mkdir -p "$(dirname "${install_dir}")"
    mv "${staging}" "${install_dir}"
  fi

  verify_install "${install_dir}"

  log ""
  log "[OK] Installed Si-Chip ${SI_CHIP_VERSION} to ${install_dir}"
  log "     SKILL.md (1) + DESIGN.md (1) + references (${EXPECTED_REFS}) + scripts (${EXPECTED_SCRIPTS}) = $((1 + 1 + EXPECTED_REFS + EXPECTED_SCRIPTS)) files"
  log "     Verify: python3 ${install_dir}/scripts/count_tokens.py --file ${install_dir}/SKILL.md --both"
  log "     Note: count_tokens.py has a soft dependency on the 'tiktoken' Python package."
  log "           Install with: pip install tiktoken (optional; falls back to a heuristic)."
}

install_codex_bridge_one() {
  # install_codex_bridge_one — installs the 2 bridge files into <scope>/.codex/.
  local install_dir
  install_dir="$(install_dir_for "codex")"

  log ""
  log "=> Installing Si-Chip Codex BRIDGE (spec §7.2 priority 3 / bridge-only) to ${install_dir}"
  log "   (Native SKILL.md runtime is §11.2 deferred; only profiles + instructions are written.)"

  check_writable_parent "${install_dir}"
  confirm_overwrite "${install_dir}/profiles" "si-chip.md"

  local staging="${install_dir}.new"

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] stage codex bridge to ${staging}"
  else
    if [[ -e "${staging}" ]]; then
      rm -rf "${staging}"
    fi
    mkdir -p "${staging}/profiles" "${staging}/instructions"
  fi

  if is_file_url; then
    fetch_codex_bridge_file "profiles/si-chip.md"            "${staging}/profiles/si-chip.md"
    fetch_codex_bridge_file "instructions/si-chip-bridge.md" "${staging}/instructions/si-chip-bridge.md"
  elif is_http_url; then
    fetch_codex_bridge_http "profiles/si-chip.md"            "${staging}/profiles/si-chip.md"
    fetch_codex_bridge_http "instructions/si-chip-bridge.md" "${staging}/instructions/si-chip-bridge.md"
  else
    die "unsupported --source-url scheme: ${SOURCE_URL} (expected http://, https://, or file://)"
  fi

  if [[ "${DRY_RUN}" -eq 0 ]]; then
    mkdir -p "${install_dir}/profiles" "${install_dir}/instructions"
    mv -f "${staging}/profiles/si-chip.md"            "${install_dir}/profiles/si-chip.md"
    mv -f "${staging}/instructions/si-chip-bridge.md" "${install_dir}/instructions/si-chip-bridge.md"
    rm -rf "${staging}"
  fi

  verify_codex_bridge_install "${install_dir}"

  log ""
  log "[OK] Installed Si-Chip Codex bridge ${SI_CHIP_VERSION} to ${install_dir}"
  log "     ${install_dir}/profiles/si-chip.md"
  log "     ${install_dir}/instructions/si-chip-bridge.md"
  log "     (${EXPECTED_CODEX_BRIDGE_FILES} bridge files; AGENTS.md remains the binding rule corpus.)"
  log "     Verify: head -n 5 ${install_dir}/profiles/si-chip.md"
}

install_one() {
  # install_one <platform>  (cursor | claude | codex)
  local platform="$1"
  case "${platform}" in
    cursor|claude) install_skill_tree_one "${platform}" ;;
    codex)         install_codex_bridge_one ;;
    *) die "internal: unknown platform ${platform}" ;;
  esac
}

uninstall_skill_tree_one() {
  # uninstall_skill_tree_one <platform>  (cursor | claude only)
  local platform="$1"
  local install_dir
  install_dir="$(install_dir_for "${platform}")"

  log ""
  log "=> Uninstalling Si-Chip (${platform}) from ${install_dir}"

  if [[ ! -d "${install_dir}" ]]; then
    log "[skip] not installed at ${install_dir}"
    return 0
  fi

  if [[ "${FORCE}" -eq 0 && "${ASSUME_YES}" -eq 0 ]]; then
    if ! is_tty; then
      die "refusing to uninstall ${install_dir} non-interactively without --yes or --force"
    fi
    local ans
    printf 'Remove %s? [y/N]: ' "${install_dir}"
    read -r ans || true
    case "${ans}" in
      y|Y|yes|YES) ;;
      *) die "aborted by user" ;;
    esac
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] rm -rf ${install_dir}"
  else
    rm -rf "${install_dir}"
  fi

  log "[OK] Uninstalled Si-Chip from ${install_dir}"
}

uninstall_codex_bridge_one() {
  # uninstall_codex_bridge_one — removes ONLY the 2 si-chip bridge files
  # from <scope>/.codex/{profiles,instructions}/. Leaves the .codex/
  # directory and any other Codex profiles untouched (we never owned them).
  local install_dir
  install_dir="$(install_dir_for "codex")"

  log ""
  log "=> Uninstalling Si-Chip Codex bridge from ${install_dir}"

  local profile_path="${install_dir}/profiles/si-chip.md"
  local bridge_path="${install_dir}/instructions/si-chip-bridge.md"

  if [[ ! -f "${profile_path}" && ! -f "${bridge_path}" ]]; then
    log "[skip] not installed at ${install_dir}"
    return 0
  fi

  if [[ "${FORCE}" -eq 0 && "${ASSUME_YES}" -eq 0 ]]; then
    if ! is_tty; then
      die "refusing to uninstall codex bridge files non-interactively without --yes or --force"
    fi
    local ans
    printf 'Remove %s and %s? [y/N]: ' "${profile_path}" "${bridge_path}"
    read -r ans || true
    case "${ans}" in
      y|Y|yes|YES) ;;
      *) die "aborted by user" ;;
    esac
  fi

  if [[ "${DRY_RUN}" -eq 1 ]]; then
    log "[dry-run] rm -f ${profile_path}"
    log "[dry-run] rm -f ${bridge_path}"
  else
    rm -f "${profile_path}"
    rm -f "${bridge_path}"
  fi

  log "[OK] Removed Si-Chip Codex bridge files from ${install_dir}"
}

uninstall_one() {
  # uninstall_one <platform>  (cursor | claude | codex)
  local platform="$1"
  case "${platform}" in
    cursor|claude) uninstall_skill_tree_one "${platform}" ;;
    codex)         uninstall_codex_bridge_one ;;
    *) die "internal: unknown platform ${platform}" ;;
  esac
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
  parse_args "$@"
  resolve_inputs
  print_banner
  check_bash_version
  check_curl

  TMPDIR_ROOT="$(mktemp -d 2>/dev/null || mktemp -d -t si-chip-install)"

  local platform
  while IFS= read -r platform; do
    if [[ "${UNINSTALL}" -eq 1 ]]; then
      uninstall_one "${platform}"
    else
      install_one "${platform}"
    fi
  done < <(platforms_for_target)

  log ""
  if [[ "${UNINSTALL}" -eq 1 ]]; then
    log "Done. Si-Chip uninstall complete."
  else
    log "Done. Si-Chip ${SI_CHIP_VERSION} installation complete."
  fi
}

main "$@"
