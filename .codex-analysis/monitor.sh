#!/bin/bash

echo "=== Monitoring 6 Parallel Codex Agents ==="
echo "Started: $(date)"
echo ""

check_count=0
max_checks=60  # Check for up to 10 minutes (60 * 10 seconds)

while [ $check_count -lt $max_checks ]; do
  check_count=$((check_count + 1))
  
  # Count active Codex processes
  active=$(ps aux | grep "codex exec" | grep -v grep | wc -l | tr -d ' ')
  
  # Count completed outputs
  completed=$(ls .codex-analysis/agent*-output.json 2>/dev/null | wc -l | tr -d ' ')
  
  # Clear screen and show status
  clear
  echo "=== Codex Agent Progress Monitor ==="
  echo "Time: $(date '+%H:%M:%S')"
  echo "Check: $check_count / $max_checks"
  echo ""
  echo "Active processes: $active"
  echo "Completed agents: $completed / 6"
  echo ""
  echo "Individual Agent Status:"
  echo "------------------------"
  
  for i in 1 2 3 4 5 6; do
    if [ -f ".codex-analysis/agent${i}-output.json" ]; then
      size=$(wc -c < ".codex-analysis/agent${i}-output.json")
      echo "✅ Agent $i: COMPLETE ($size bytes)"
    elif [ -f ".codex-analysis/agent${i}-log.txt" ]; then
      lines=$(wc -l < ".codex-analysis/agent${i}-log.txt" 2>/dev/null || echo "0")
      echo "⏳ Agent $i: Running ($lines log lines)"
    else
      echo "❌ Agent $i: Not started"
    fi
  done
  
  # Check if all completed
  if [ "$completed" -eq 6 ]; then
    echo ""
    echo "🎉 All 6 agents completed!"
    echo "Completed at: $(date)"
    exit 0
  fi
  
  # Wait 10 seconds before next check
  sleep 10
done

echo ""
echo "⚠️  Timeout reached after $(($max_checks * 10)) seconds"
echo "Completed: $completed / 6 agents"
