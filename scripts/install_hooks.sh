#!/bin/sh
# Installs the secret-scan pre-commit hook for this clone. Run once per clone.
set -e
root="$(git rev-parse --show-toplevel)"
chmod +x "$root/scripts/hooks/pre-commit" "$root/scripts/"*.py 2>/dev/null || true
git -C "$root" config core.hooksPath scripts/hooks
echo "Secret-scan hook installed (core.hooksPath = scripts/hooks)."
