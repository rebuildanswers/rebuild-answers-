#!/bin/sh
# GitHub push diagnostic + setup. POSIX sh — works in bash, zsh, sh.
# Reports what is wrong instead of failing with one vague line.
# The token is never echoed, never written to disk, never put in history.

REPO_OWNER="rebuildanswers"
REPO_NAME="rebuild-answers-"

printf '\n=== GitHub push setup ===\n\n'
printf 'Paste your token, then press Enter.\n'
printf 'Nothing will appear on screen. That is normal.\n\n'
printf 'Token: '
stty -echo 2>/dev/null
read TOKEN
stty echo 2>/dev/null
printf '\n\n'

# ---- 1. did we receive anything at all? --------------------------------
LEN=$(printf '%s' "$TOKEN" | wc -c | tr -d ' ')
PREFIX=$(printf '%s' "$TOKEN" | cut -c1-4)

printf -- '--- 1. what you pasted ---\n'
printf '  length : %s characters\n' "$LEN"
printf '  starts : %s...\n' "$PREFIX"

if [ "$LEN" -lt 20 ]; then
  printf '\n  PROBLEM: that is too short to be a token.\n'
  printf '  A classic token is ~40 chars and starts "ghp_".\n'
  printf '  A fine-grained token is ~93 chars and starts "github_pat_".\n'
  printf '  Nothing pasted? Try Cmd+V, or right-click > Paste.\n\n'
  exit 1
fi

case "$PREFIX" in
  ghp_) printf '  type   : classic token (good)\n' ;;
  gith) printf '  type   : fine-grained token\n'
        printf '  NOTE: fine-grained tokens need the ORG to approve them.\n'
        printf '        If this fails, make a CLASSIC token instead.\n' ;;
  *)    printf '\n  PROBLEM: does not start with ghp_ or github_pat_.\n'
        printf '  That looks like a password, not a token.\n'
        printf '  Tokens are shown ONCE on a green background right after\n'
        printf '  you click "Generate token".\n\n'
        exit 1 ;;
esac

# ---- 2. does GitHub accept it? -----------------------------------------
printf -- '\n--- 2. does GitHub accept it? ---\n'
HDRS=$(curl -s -D - -o /tmp/ghbody.$$ -H "Authorization: Bearer $TOKEN" \
        -H "User-Agent: gh-setup" https://api.github.com/user)
CODE=$(printf '%s' "$HDRS" | awk 'NR==1{print $2}')
SCOPES=$(printf '%s' "$HDRS" | tr -d '\r' | awk -F': ' 'tolower($1)=="x-oauth-scopes"{print $2}')
LOGIN=$(python3 -c "import json;print(json.load(open('/tmp/ghbody.$$')).get('login',''))" 2>/dev/null)
rm -f /tmp/ghbody.$$

printf '  http   : %s\n' "$CODE"
if [ "$CODE" != "200" ]; then
  printf '\n  PROBLEM: GitHub rejected this token.\n'
  printf '  Most likely it was revoked, expired, or copied incompletely.\n'
  printf '  Make a fresh one: https://github.com/settings/tokens/new\n\n'
  exit 1
fi
printf '  user   : %s\n' "$LOGIN"
printf '  scopes : %s\n' "${SCOPES:-(none)}"

case "$SCOPES" in
  *repo*) printf '  repo scope present (good)\n' ;;
  *) printf '\n  PROBLEM: this token has no "repo" scope, so it cannot push.\n'
     printf '  Make a new one and tick the FIRST checkbox, "repo".\n'
     printf '  https://github.com/settings/tokens/new\n\n'
     exit 1 ;;
esac

# ---- 3. does the repo exist and can this token see it? ------------------
printf -- '\n--- 3. the repository ---\n'
RCODE=$(curl -s -o /tmp/ghrepo.$$ -w '%{http_code}' \
        -H "Authorization: Bearer $TOKEN" -H "User-Agent: gh-setup" \
        "https://api.github.com/repos/$REPO_OWNER/$REPO_NAME")
printf '  %s/%s -> HTTP %s\n' "$REPO_OWNER" "$REPO_NAME" "$RCODE"

if [ "$RCODE" = "404" ]; then
  printf '\n  PROBLEM: that repository does not exist (or this account\n'
  printf '  cannot see it). Create it first:\n'
  printf '    1. https://github.com/organizations/plan  -> Free -> "%s"\n' "$REPO_OWNER"
  printf '    2. https://github.com/new -> owner "%s", name "%s"\n' "$REPO_OWNER" "$REPO_NAME"
  printf '       Public. Do NOT tick README/gitignore/license.\n'
  printf '\n  Your other repos, to check the owner name:\n'
  curl -s -H "Authorization: Bearer $TOKEN" -H "User-Agent: gh-setup" \
    "https://api.github.com/user/repos?per_page=100&sort=updated" \
    | python3 -c "import json,sys
try:
  rs=json.load(sys.stdin)
  rs=[r for r in rs if isinstance(r,dict)]
  print('\n'.join('    '+r['full_name']+('  (private)' if r['private'] else '') for r in rs[:15]) or '    (none)')
except Exception: print('    (could not list)')" 2>/dev/null
  printf '\n'
  rm -f /tmp/ghrepo.$$
  exit 1
fi
PRIV=$(python3 -c "import json;print(json.load(open('/tmp/ghrepo.$$')).get('private'))" 2>/dev/null)
rm -f /tmp/ghrepo.$$
printf '  private: %s\n' "$PRIV"
[ "$PRIV" = "True" ] && printf '  NOTE: site links call this open source. Make it Public before launch.\n'

# ---- 4. store + push ----------------------------------------------------
printf -- '\n--- 4. storing credential and pushing ---\n'
printf 'protocol=https\nhost=github.com\nusername=%s\npassword=%s\n' "$LOGIN" "$TOKEN" \
  | git credential-osxkeychain store
printf '  credential stored for %s\n\n' "$LOGIN"
git push -u origin main
