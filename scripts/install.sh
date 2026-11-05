#!/usr/bin/env sh
# Install the ChainLink skills into a Claude Code skills directory.
set -eu

usage() {
  cat <<USAGE
Usage: install.sh [options] [skill ...]

Installs skills into ~/.claude/skills by default.
With no skill names, every skill in skills/ is installed.

Options:
  -p, --project      Install to ./.claude/skills (current directory) instead
  -t, --target DIR   Install to DIR (overrides --project)
  -l, --link         Symlink instead of copying (stays in sync with this repo)
  -f, --force        Replace skills that already exist
  -h, --help         Show this help
USAGE
}

src="$(cd "$(dirname "$0")/../skills" && pwd)"
target="$HOME/.claude/skills"
link=0
force=0
names=""

while [ $# -gt 0 ]; do
  case "$1" in
    -p|--project) target="$PWD/.claude/skills" ;;
    -t|--target) [ $# -ge 2 ] || { echo "--target needs a directory" >&2; exit 2; }; target="$2"; shift ;;
    -l|--link) link=1 ;;
    -f|--force) force=1 ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) names="$names $1" ;;
  esac
  shift
done

if [ -z "$names" ]; then
  for d in "$src"/*/; do names="$names $(basename "$d")"; done
fi

mkdir -p "$target"

for name in $names; do
  if [ ! -d "$src/$name" ]; then
    echo "Unknown skill: $name" >&2
    exit 1
  fi
  dest="$target/$name"
  if [ -e "$dest" ] || [ -L "$dest" ]; then
    if [ "$force" -eq 1 ]; then
      rm -rf "$dest"
    else
      echo "skip  $name (exists; use --force to replace)"
      continue
    fi
  fi
  if [ "$link" -eq 1 ]; then
    ln -s "$src/$name" "$dest"
    echo "link  $name -> $dest"
  else
    cp -R "$src/$name" "$dest"
    echo "copy  $name -> $dest"
  fi
done
