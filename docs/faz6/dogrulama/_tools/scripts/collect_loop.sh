#!/bin/zsh
cd "$(dirname $0)"
while true; do
  python3 collect.py >> collect.log 2>&1
  if grep -q bitti fetch_days.log && [ $(ls tick/*.json | wc -l) -ge 135 ]; then echo "LOOP BITTI" >> collect.log; break; fi
  if grep -q bitti fetch_days.log; then python3 collect.py >> collect.log 2>&1; echo "LOOP BITTI" >> collect.log; break; fi
  sleep 30
done
