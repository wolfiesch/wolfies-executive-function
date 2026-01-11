# Google Daemon Benchmark Results

Generated: 2026-01-08 17:48:48

## Performance Comparison

| Workload | CLI Cold | CLI+Daemon | Raw Daemon | MCP | Speedup (CLI→Daemon) |
|----------|----------|------------|------------|-----|---------------------|
| CALENDAR_FREE_30MIN | 1003ms | 111ms | 69ms | - | **9.0x** |
| CALENDAR_FREE_60MIN | 1049ms | 116ms | 70ms | - | **9.0x** |
| CALENDAR_TODAY | 1130ms | 126ms | 69ms | - | **9.0x** |
| CALENDAR_WEEK | 1028ms | 115ms | 67ms | - | **8.9x** |
| GMAIL_LIST_10 | 1177ms | 318ms | 261ms | - | **3.7x** |
| GMAIL_LIST_25 | 5852ms | 401ms | 517ms | - | **14.6x** |
| GMAIL_LIST_5 | 1471ms | 285ms | 251ms | - | **5.2x** |
| GMAIL_SEARCH_SIMPLE | 1161ms | 287ms | 243ms | - | **4.1x** |
| GMAIL_UNREAD_COUNT | 1032ms | 167ms | 123ms | - | **6.2x** |


## Detailed Statistics

| Workload | Mode | Mean | P50 | P95 | P99 | StdDev | OK% |
|----------|------|------|-----|-----|-----|--------|-----|
| CALENDAR_FREE_30MIN | cli_cold | 1003.1ms | 988.4ms | 1026.0ms | 1026.0ms | 36.5ms | 100% |
| CALENDAR_FREE_30MIN | cli_daemon | 111.3ms | 111.3ms | 113.7ms | 113.7ms | 2.5ms | 100% |
| CALENDAR_FREE_30MIN | daemon_raw | 68.6ms | 70.3ms | 71.2ms | 71.2ms | 4.7ms | 100% |
| CALENDAR_FREE_60MIN | cli_cold | 1049.4ms | 1041.7ms | 1044.7ms | 1044.7ms | 62.0ms | 100% |
| CALENDAR_FREE_60MIN | cli_daemon | 116.4ms | 114.7ms | 121.0ms | 121.0ms | 9.2ms | 100% |
| CALENDAR_FREE_60MIN | daemon_raw | 69.6ms | 70.1ms | 75.3ms | 75.3ms | 6.2ms | 100% |
| CALENDAR_TODAY | cli_cold | 1129.7ms | 1137.2ms | 1151.0ms | 1151.0ms | 73.2ms | 100% |
| CALENDAR_TODAY | cli_daemon | 125.9ms | 117.4ms | 132.2ms | 132.2ms | 19.4ms | 100% |
| CALENDAR_TODAY | daemon_raw | 69.0ms | 69.5ms | 71.7ms | 71.7ms | 8.2ms | 100% |
| CALENDAR_WEEK | cli_cold | 1028.2ms | 1001.3ms | 1003.0ms | 1003.0ms | 86.4ms | 100% |
| CALENDAR_WEEK | cli_daemon | 115.0ms | 116.3ms | 117.8ms | 117.8ms | 5.0ms | 100% |
| CALENDAR_WEEK | daemon_raw | 66.8ms | 67.7ms | 68.3ms | 68.3ms | 7.0ms | 100% |
| GMAIL_LIST_10 | cli_cold | 1177.2ms | 1171.6ms | 1177.9ms | 1177.9ms | 20.6ms | 100% |
| GMAIL_LIST_10 | cli_daemon | 317.6ms | 312.5ms | 327.9ms | 327.9ms | 20.8ms | 100% |
| GMAIL_LIST_10 | daemon_raw | 261.0ms | 258.9ms | 265.6ms | 265.6ms | 14.5ms | 100% |
| GMAIL_LIST_25 | cli_cold | 5852.0ms | 1327.4ms | 1359.1ms | 1359.1ms | 10151.0ms | 80% |
| GMAIL_LIST_25 | cli_daemon | 400.6ms | 399.4ms | 410.5ms | 410.5ms | 11.7ms | 100% |
| GMAIL_LIST_25 | daemon_raw | 517.4ms | 396.0ms | 667.9ms | 667.9ms | 184.8ms | 100% |
| GMAIL_LIST_5 | cli_cold | 1470.6ms | 1291.0ms | 1363.7ms | 1363.7ms | 537.5ms | 100% |
| GMAIL_LIST_5 | cli_daemon | 285.1ms | 283.2ms | 287.3ms | 287.3ms | 18.1ms | 100% |
| GMAIL_LIST_5 | daemon_raw | 251.1ms | 242.9ms | 250.2ms | 250.2ms | 30.3ms | 100% |
| GMAIL_SEARCH_SIMPLE | cli_cold | 1161.5ms | 1161.0ms | 1161.3ms | 1161.3ms | 63.0ms | 100% |
| GMAIL_SEARCH_SIMPLE | cli_daemon | 286.5ms | 290.1ms | 292.2ms | 292.2ms | 8.4ms | 100% |
| GMAIL_SEARCH_SIMPLE | daemon_raw | 242.7ms | 241.9ms | 243.6ms | 243.6ms | 12.1ms | 100% |
| GMAIL_UNREAD_COUNT | cli_cold | 1031.6ms | 1037.5ms | 1046.2ms | 1046.2ms | 19.3ms | 100% |
| GMAIL_UNREAD_COUNT | cli_daemon | 167.3ms | 170.6ms | 174.3ms | 174.3ms | 14.2ms | 100% |
| GMAIL_UNREAD_COUNT | daemon_raw | 123.0ms | 123.4ms | 123.6ms | 123.6ms | 10.8ms | 100% |


## Summary

- Average CLI Cold: 1656ms
- Average CLI Daemon: 214ms
- **Average Speedup: 7.7x**