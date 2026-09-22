#!/usr/bin/env bash
# Rename the brand everywhere, in one pass.
#
#   ./rename.sh "New Name" newdomain.com [github-org]
#        dry run — shows every change, writes nothing
#
#   ./rename.sh "New Name" newdomain.com [github-org] --apply
#        actually does it
#
# Handles all four forms the current name appears in. The current values live
# in the OLD_* constants below and are rewritten on every --apply, so this
# comment stays generic rather than going stale:
#   OLD_NAME   prose, titles, schema
#   OLD_DOM    domain, canonicals, emails, llms.txt, sitemap
#   OLD_SLUG   github org slug, cal.com path
#   OLD_FIRST/OLD_REST   the split logo markup in every page header
#
# Run with no arguments to print what it currently targets.
#
# Dry run first. Always.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OLD_NAME="Rebuild Answers"
OLD_DOM="rebuildanswers.com"
OLD_SLUG="rebuildanswers"
OLD_FIRST="Rebuild"
OLD_REST="Answers"

if [ $# -eq 0 ]; then
  echo "rename.sh currently targets:"
  echo "  name    $OLD_NAME"
  echo "  domain  $OLD_DOM"
  echo "  slug    $OLD_SLUG"
  echo
  echo "usage: ./rename.sh \"New Name\" newdomain.com [github-org] [--apply]"
  exit 0
fi

# Escape regex metacharacters so a literal string is matched literally.
# Without this, a domain like "example.ai" matches "example-ai" too, because
# an unescaped "." is "any character" -- which silently ate the slug rule
# on 2026-09-22 and rewrote github.com/<slug> into github.com/<domain>.
rx() { printf '%s' "$1" | sed 's/[.[\*^$\/&]/\\&/g'; }

NEW_NAME="${1:-}"
NEW_DOM="${2:-}"
NEW_SLUG="${3:-}"
APPLY=""
for a in "$@"; do [ "$a" = "--apply" ] && APPLY=1; done
[ "${NEW_SLUG:-}" = "--apply" ] && NEW_SLUG=""

if [ -z "$NEW_NAME" ] || [ -z "$NEW_DOM" ]; then
  sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^#\{1,\} \{0,1\}//'
  exit 1
fi

# slug defaults to the name, lowercased, spaces -> hyphens
if [ -z "$NEW_SLUG" ]; then
  NEW_SLUG="$(printf '%s' "$NEW_NAME" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')"
fi

# split the new name for the logo markup: first word, then the rest
NEW_FIRST="${NEW_NAME%% *}"
NEW_REST="${NEW_NAME#* }"
[ "$NEW_FIRST" = "$NEW_NAME" ] && NEW_REST=""

echo "  name    $OLD_NAME  ->  $NEW_NAME"
echo "  domain  $OLD_DOM  ->  $NEW_DOM"
echo "  slug    $OLD_SLUG  ->  $NEW_SLUG"
if [ -n "$NEW_REST" ]; then
  echo "  logo    ${OLD_FIRST}<span> ${OLD_REST}</span>  ->  ${NEW_FIRST}<span> ${NEW_REST}</span>"
else
  echo "  logo    single-word name — span wrapper removed"
fi
echo

FILES=$(grep -rl "$OLD_NAME\|$OLD_DOM\|$OLD_SLUG" \
          --exclude-dir=.venv --exclude-dir=.git --exclude=rename.sh \
          --exclude=answer-layer-install.sh "$HERE" 2>/dev/null | sort)

[ -z "$FILES" ] && { echo "nothing to rename."; exit 0; }

TOTAL=0
while IFS= read -r f; do
  n=$(grep -c "$OLD_NAME\|$OLD_DOM\|$OLD_SLUG" "$f" 2>/dev/null || true)
  [ "${n:-0}" -eq 0 ] && continue
  printf '  %-58s %s lines\n' "${f#$HERE/}" "$n"
  TOTAL=$((TOTAL + n))
done <<< "$FILES"
echo
echo "  $TOTAL lines across $(printf '%s\n' "$FILES" | wc -l | tr -d ' ') files"

if [ -z "$APPLY" ]; then
  echo
  echo "  DRY RUN — nothing written. Re-run with --apply to commit the change."
  echo
  echo "  Sample of what changes:"
  printf '%s\n' "$FILES" | head -1 | while IFS= read -r f; do
    grep -n "$OLD_NAME\|$OLD_DOM\|$OLD_SLUG" "$f" | head -4 | sed 's/^/    /'
  done
  exit 0
fi

echo
while IFS= read -r f; do
  # logo markup first — it is the most specific pattern
  if [ -n "$NEW_REST" ]; then
    LC_ALL=C sed -i '' "s|${OLD_FIRST}<span>\&nbsp;${OLD_REST}</span>|${NEW_FIRST}<span>\&nbsp;${NEW_REST}</span>|g" "$f"
  else
    LC_ALL=C sed -i '' "s|${OLD_FIRST}<span>\&nbsp;${OLD_REST}</span>|${NEW_FIRST}|g" "$f"
  fi
  # then domain (before name, so the domain isn't half-caught by a name rule)
  # ORDER IS LOAD-BEARING: most specific pattern first.
  # The domain ("acme.com") is a superstring of the slug ("acme"), so the
  # domain must be rewritten first or the slug rule eats "hello@acme.com"
  # and turns it into "hello@newslug.com".
  # And every pattern must be regex-escaped -- an unescaped "." in the
  # domain matches any character, which is what rewrote github.com/<slug>
  # into github.com/<domain> on 2026-09-22.
  LC_ALL=C sed -i '' "s|$(rx "$OLD_DOM")|${NEW_DOM}|g" "$f"
  LC_ALL=C sed -i '' "s|$(rx "$OLD_SLUG")|${NEW_SLUG}|g" "$f"
  LC_ALL=C sed -i '' "s|$(rx "$OLD_NAME")|${NEW_NAME}|g" "$f"
  echo "  rewritten  ${f#$HERE/}"
done <<< "$FILES"

# Update this script's own constants so the NEXT rename works. Without this,
# a second rename would still be hunting for the original name and find nothing.
SELF="${BASH_SOURCE[0]}"
LC_ALL=C sed -i '' \
  -e "s|^OLD_NAME=\".*\"$|OLD_NAME=\"${NEW_NAME}\"|" \
  -e "s|^OLD_DOM=\".*\"$|OLD_DOM=\"${NEW_DOM}\"|" \
  -e "s|^OLD_SLUG=\".*\"$|OLD_SLUG=\"${NEW_SLUG}\"|" \
  -e "s|^OLD_FIRST=\".*\"$|OLD_FIRST=\"${NEW_FIRST}\"|" \
  -e "s|^OLD_REST=\".*\"$|OLD_REST=\"${NEW_REST}\"|" \
  "$SELF"
echo "  rewritten  rename.sh (constants updated for the next rename)"

# The brand name is rendered into the social card, so regenerate it.
OG="$HERE/answer-layer/scripts/make_og_image.py"
PYBIN="$HERE/.venv/bin/python"
if [ -x "$PYBIN" ] && [ -f "$OG" ]; then
  if "$PYBIN" -c 'import PIL' 2>/dev/null; then
    "$PYBIN" "$OG" "$NEW_NAME" "$NEW_DOM" "$HERE/site/og.png" >/dev/null 2>&1 \
      && echo "  regenerated  site/og.png" \
      || echo "  WARN: og.png regeneration failed — run make_og_image.py by hand"
  else
    echo "  NOTE: Pillow not installed; site/og.png still shows the OLD name."
    echo "        Fix: .venv/bin/pip install Pillow && .venv/bin/python $OG \"$NEW_NAME\" $NEW_DOM site/og.png"
  fi
fi

echo
echo "  done. Now check by hand:"
echo "    - the <title> on each page still reads well"
echo "    - schema.org blocks in index.html and pricing.html"
echo "    - the cal.com booking URL (slug changed, the account may not have)"
echo "    - the GitHub org actually exists at the new slug"
echo "    - rename the project folder itself, if you want it to match"
