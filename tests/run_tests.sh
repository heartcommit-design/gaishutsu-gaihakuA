#!/usr/bin/env bash
# 使い方: bash tests/run_tests.sh            … suite.txt の全部
#         bash tests/run_tests.sh test_undo  … 1本だけ
# 合格の条件: 終了コード0、Traceback/AssertionErrorなし、"errors [" で始まる行がすべて "errors []"（画面のJSエラーなし）
cd "$(dirname "$0")" || exit 1
mkdir -p out
if [ $# -gt 0 ]; then LIST="$*"; else LIST=$(grep -v '^\s*#' suite.txt | grep -v '^\s*$'); fi
pass=0; fail=0; failed=""
for t in $LIST; do
  t=${t%.py}
  log="out/$t.log"
  ( cd out && timeout 300 python3 "../$t.py" ) >"$log" 2>&1 </dev/null
  code=$?
  bad=0
  [ $code -ne 0 ] && bad=1
  grep -q "Traceback\|AssertionError" "$log" && bad=1
  grep -o "errors \[.*" "$log" | grep -vq "^errors \[\]" && bad=1
  if [ $bad -eq 0 ]; then pass=$((pass+1)); echo "OK   $t"; else fail=$((fail+1)); failed="$failed $t"; echo "NG   $t  (exit $code, ログ: tests/$log)"; fi
done
echo "合格 $pass / 不合格 $fail"
[ $fail -eq 0 ] || { echo "不合格:$failed"; exit 1; }
