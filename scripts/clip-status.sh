#!/usr/bin/env bash
# 列出台账：EasyWebClipper/ 里哪些剪藏还没判定。
# 只读，不修改任何文件。用法：./scripts/clip-status.sh

set -euo pipefail
cd "$(dirname "$0")/.."

idx="wiki/index.md"
[ -f "$idx" ] || { echo "找不到 $idx"; exit 1; }

total=0
pending=0
printf '%s\n' "EasyWebClipper/ 判定台账"
printf '%s\n' "----------------------------------------"

for f in EasyWebClipper/*.md; do
  [ -e "$f" ] || continue
  total=$((total + 1))
  base=$(basename "$f")

  if grep -qF "$base" "$idx"; then
    printf '  已判  %s\n' "$base"
    continue
  fi

  pending=$((pending + 1))
  lines=$(wc -l < "$f" | tr -d ' ')
  src=$(awk -F'^source: *' '/^source:/{print $2; exit}' "$f" | sed 's|https\?://\([^/]*\).*|\1|')
  title=$(awk -F'^title: *' '/^title:/{print $2; exit}' "$f" | tr -d '"')
  printf '  待判  %s\n' "$base"
  printf '        %s 行 | %s | %s\n' "$lines" "${src:-未知来源}" "${title:-无标题}"
done

printf '%s\n' "----------------------------------------"
printf '共 %s 篇，待判 %s 篇\n' "$total" "$pending"
