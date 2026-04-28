#!/usr/bin/env bash
# Si-Chip installer
#   Installs the Si-Chip Skill payload (SKILL.md + 5 references + 3 scripts)
#   into a Cursor and/or Claude Code skills directory (global or repo scope).
#
#   Source of truth: https://github.com/YoRHa-Agents/Si-Chip
#   Spec:            .local/research/spec_v0.1.0.md
#
#   Per spec section 7.2, only Cursor and Claude Code are supported install
#   targets in v0.1; Codex is bridge-only and intentionally NOT a target here.

set -euo pipefail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SI_CHIP_VERSION_DEFAULT="v0.1.1"
SOURCE_URL_DEFAULT="https://yorha-agents.github.io/Si-Chip"

MANIFEST=(
  "SKILL.md"
  "references/basic-ability-profile.md"
  "references/self-dogfood-protocol.md"
  "references/metrics-r6-summary.md"
  "references/router-test-r8-summary.md"
  "references/half-retirement-r9-summary.md"
  "scripts/profile_static.py"
  "scripts/count_tokens.py"
  "scripts/aggregate_eval.py"
)

EXPECTED_REFS=5
EXPECTED_SCRIPTS=3

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
Si-Chip installer v0.1.0

Usage:
  curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash
  curl -fsSL https://yorha-agents.github.io/Si-Chip/install.sh | bash -s -- --target cursor --scope global --yes
  ./install.sh --target claude --scope repo --repo-root /path/to/myproject --yes

Flags:
  --target cursor|claude|both    Which platform to install for
  --scope global|repo            Where to install
  --repo-root <path>             Repo root (required for --scope repo)
  --version <tag>                Si-Chip version to install (default: v0.1.0)
  --source-url <url>             Override download base (default: pages URL)
  --yes, -y                      Non-interactive
  --dry-run                      Print actions without writing
  --force                        Overwrite existing install without prompting
  --uninstall                    Remove the installed dir for chosen target/scope
  --help, -h                     This help
  --version-info                 Print installer version

Examples:
  # Install both targets globally
  ./install.sh --target both --scope global --yes

  # Install Cursor only into a specific repo
  ./install.sh --target cursor --scope repo --repo-root ~/code/myrepo --yes

  # Dry-run interactive install
  ./install.sh --dry-run

  # Uninstall from global Claude Code
  ./install.sh --target claude --scope global --uninstall --yes

Payload delivery:
  Over HTTP(S), the installer downloads a single tarball at
  <source-url>/skills/si-chip-<version>.tar.gz and extracts it.
  Over file://, it copies individual files from <source-url>/skills/si-chip/.

Si-Chip is governed by the spec at:
  https://github.com/YoRHa-Agents/Si-Chip/blob/main/.local/research/spec_v0.1.0.md
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

prompt_target() {
  local choice
  log "Select target platform:"
  log "  1) Cursor"
  log "  2) Claude Code"
  log "  3) Both"
  printf 'Choice [1]: '
  read -r choice || true
  case "${choice:-1}" in
    1|"") TARGET="cursor" ;;
    2)    TARGET="claude" ;;
    3)    TARGET="both" ;;
    *)    die "invalid choice: ${choice}" ;;
  esac
}

prompt_scope() {
  local choice
  log "Select install scope:"
  log "  1) Global (~/.<platform>/skills/si-chip)"
  log "  2) Repo  (./<repo>/.<platform>/skills/si-chip)"
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
  if [[ -n "${TARGET}" && "${TARGET}" != "cursor" && "${TARGET}" != "claude" && "${TARGET}" != "both" ]]; then
    die "--target must be one of: cursor | claude | both (got: ${TARGET})"
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
    # Make REPO_ROOT absolute
    REPO_ROOT="$(cd "${REPO_ROOT}" && pwd)"
  fi
}

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

install_dir_for() {
  # install_dir_for <platform>  -> echoes absolute path
  local platform="$1"
  local sub
  case "${platform}" in
    cursor) sub=".cursor" ;;
    claude) sub=".claude" ;;
    *) die "internal: unknown platform ${platform}" ;;
  esac
  if [[ "${SCOPE}" == "global" ]]; then
    if [[ -z "${HOME:-}" ]]; then
      die "HOME is not set; cannot resolve global install dir"
    fi
    printf '%s/%s/skills/si-chip\n' "${HOME}" "${sub}"
  else
    printf '%s/%s/skills/si-chip\n' "${REPO_ROOT}" "${sub}"
  fi
}

platforms_for_target() {
  case "${TARGET}" in
    cursor) printf 'cursor\n' ;;
    claude) printf 'claude\n' ;;
    both)   printf 'cursor\nclaude\n' ;;
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
    return 0  # will be created later
  fi
  if [[ ! -w "${parent}" ]]; then
    die "parent directory is not writable: ${parent}"
  fi
}

confirm_overwrite() {
  # confirm_overwrite <install_dir>
  local install_dir="$1"
  if [[ ! -d "${install_dir}" ]]; then
    return 0
  fi
  if [[ ! -f "${install_dir}/SKILL.md" ]]; then
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
  # tarball_basename -> echoes "si-chip-<version>.tar.gz" (strips leading v)
  printf 'si-chip-%s.tar.gz\n' "${SI_CHIP_VERSION#v}"
}

fetch_one() {
  # fetch_one <relpath> <dst-abs>  (file:// path only)
  local rel="$1"
  local dst="$2"
  local src
  # Strip leading file://
  local base="${SOURCE_URL#file://}"
  src="${base}/skills/si-chip/${rel}"
  if [[ ! -f "${src}" ]]; then
    die "missing source file: ${src}"
  fi
  run mkdir -p "$(dirname "${dst}")"
  run cp "${src}" "${dst}"
}

stage_payload_file() {
  # stage_payload_file <staging-dir>
  # file:// path: copy each manifest entry from <source-url>/skills/si-chip/.
  local staging="$1"
  local rel
  for rel in "${MANIFEST[@]}"; do
    fetch_one "${rel}" "${staging}/${rel}"
  done
}

stage_payload_http() {
  # stage_payload_http <staging-dir>
  # HTTP(S) path: download the release tarball and extract into <staging-dir>.
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
  if ! tar -xzf "${tarball_path}" -C "${staging}"; then
    die "failed to extract ${tarball_name}"
  fi
}

stage_payload() {
  # stage_payload <staging-dir>
  # Dispatches to the file:// copy loop or the HTTP(S) tarball download.
  local staging="$1"
  if is_file_url; then
    stage_payload_file "${staging}"
  elif is_http_url; then
    stage_payload_http "${staging}"
  else
    die "unsupported --source-url scheme: ${SOURCE_URL} (expected http://, https://, or file://)"
  fi
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

install_one() {
  # install_one <platform>
  local platform="$1"
  local install_dir
  install_dir="$(install_dir_for "${platform}")"

  log ""
  log "=> Installing Si-Chip (${platform}) to ${install_dir}"

  check_writable_parent "${install_dir}"
  confirm_overwrite "${install_dir}"

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
  log "     SKILL.md (1) + references (${EXPECTED_REFS}) + scripts (${EXPECTED_SCRIPTS}) = 9 files"
  log "     Verify: python3 ${install_dir}/scripts/count_tokens.py --file ${install_dir}/SKILL.md --both"
  log "     Note: count_tokens.py has a soft dependency on the 'tiktoken' Python package."
  log "           Install with: pip install tiktoken (optional; falls back to a heuristic)."
}

uninstall_one() {
  # uninstall_one <platform>
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
