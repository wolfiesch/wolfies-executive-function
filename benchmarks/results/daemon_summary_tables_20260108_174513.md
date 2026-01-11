# Google Daemon Benchmark Results

Generated: 2026-01-08 17:45:13

## Performance Comparison

| Workload | CLI Cold | CLI+Daemon | Raw Daemon | MCP | Speedup (CLI→Daemon) |
|----------|----------|------------|------------|-----|---------------------|
| CALENDAR_FREE_30MIN | 1069ms | 40ms | 65ms | - | **26.8x** |
| CALENDAR_FREE_60MIN | 1001ms | 38ms | 74ms | - | **26.2x** |
| CALENDAR_TODAY | 1021ms | 117ms | 107ms | - | **8.7x** |
| CALENDAR_WEEK | 1109ms | 112ms | 122ms | - | **9.9x** |
| GMAIL_LIST_10 | 1200ms | 309ms | 255ms | - | **3.9x** |
| GMAIL_LIST_25 | 1361ms | 457ms | 392ms | - | **3.0x** |
| GMAIL_LIST_5 | 1269ms | 300ms | 245ms | - | **4.2x** |
| GMAIL_SEARCH_SIMPLE | 38ms | 39ms | 227ms | - | **1.0x** |
| GMAIL_UNREAD_COUNT | 1089ms | 182ms | 121ms | - | **6.0x** |


## Detailed Statistics

| Workload | Mode | Mean | P50 | P95 | P99 | StdDev | OK% |
|----------|------|------|-----|-----|-----|--------|-----|
| CALENDAR_FREE_30MIN | cli_cold | 1069.0ms | 1033.3ms | 1033.3ms | 1033.3ms | 94.7ms | 100% |
| CALENDAR_FREE_30MIN | cli_daemon | 39.9ms | 39.9ms | 39.9ms | 39.9ms | 1.2ms | 0% |
| CALENDAR_FREE_30MIN | daemon_raw | 64.7ms | 65.4ms | 65.4ms | 65.4ms | 3.2ms | 100% |
| CALENDAR_FREE_60MIN | cli_cold | 1001.0ms | 1009.9ms | 1009.9ms | 1009.9ms | 17.2ms | 100% |
| CALENDAR_FREE_60MIN | cli_daemon | 38.2ms | 38.1ms | 38.1ms | 38.1ms | 0.4ms | 0% |
| CALENDAR_FREE_60MIN | daemon_raw | 73.6ms | 75.1ms | 75.1ms | 75.1ms | 6.3ms | 100% |
| CALENDAR_TODAY | cli_cold | 1021.0ms | 1029.7ms | 1029.7ms | 1029.7ms | 15.1ms | 100% |
| CALENDAR_TODAY | cli_daemon | 117.1ms | 119.5ms | 119.5ms | 119.5ms | 5.1ms | 100% |
| CALENDAR_TODAY | daemon_raw | 107.4ms | 105.8ms | 105.8ms | 105.8ms | 15.8ms | 100% |
| CALENDAR_WEEK | cli_cold | 1109.2ms | 1091.6ms | 1091.6ms | 1091.6ms | 173.5ms | 100% |
| CALENDAR_WEEK | cli_daemon | 112.2ms | 111.9ms | 111.9ms | 111.9ms | 2.5ms | 100% |
| CALENDAR_WEEK | daemon_raw | 121.6ms | 69.3ms | 69.3ms | 69.3ms | 91.1ms | 100% |
| GMAIL_LIST_10 | cli_cold | 1200.3ms | 1192.7ms | 1192.7ms | 1192.7ms | 53.2ms | 100% |
| GMAIL_LIST_10 | cli_daemon | 308.6ms | 302.2ms | 302.2ms | 302.2ms | 17.6ms | 100% |
| GMAIL_LIST_10 | daemon_raw | 255.5ms | 261.2ms | 261.2ms | 261.2ms | 13.7ms | 100% |
| GMAIL_LIST_25 | cli_cold | 1361.4ms | 1323.0ms | 1323.0ms | 1323.0ms | 95.7ms | 100% |
| GMAIL_LIST_25 | cli_daemon | 456.5ms | 441.2ms | 441.2ms | 441.2ms | 82.5ms | 100% |
| GMAIL_LIST_25 | daemon_raw | 391.7ms | 385.6ms | 385.6ms | 385.6ms | 25.5ms | 100% |
| GMAIL_LIST_5 | cli_cold | 1269.0ms | 1198.8ms | 1198.8ms | 1198.8ms | 129.6ms | 100% |
| GMAIL_LIST_5 | cli_daemon | 299.7ms | 291.4ms | 291.4ms | 291.4ms | 16.3ms | 100% |
| GMAIL_LIST_5 | daemon_raw | 244.9ms | 247.3ms | 247.3ms | 247.3ms | 5.5ms | 100% |
| GMAIL_SEARCH_SIMPLE | cli_cold | 37.9ms | 37.0ms | 37.0ms | 37.0ms | 1.9ms | 0% |
| GMAIL_SEARCH_SIMPLE | cli_daemon | 38.6ms | 38.8ms | 38.8ms | 38.8ms | 1.2ms | 0% |
| GMAIL_SEARCH_SIMPLE | daemon_raw | 226.6ms | 226.3ms | 226.3ms | 226.3ms | 0.5ms | 100% |
| GMAIL_UNREAD_COUNT | cli_cold | 1089.3ms | 1063.0ms | 1063.0ms | 1063.0ms | 73.5ms | 100% |
| GMAIL_UNREAD_COUNT | cli_daemon | 182.1ms | 176.2ms | 176.2ms | 176.2ms | 21.7ms | 100% |
| GMAIL_UNREAD_COUNT | daemon_raw | 120.6ms | 118.9ms | 118.9ms | 118.9ms | 3.4ms | 100% |


## Summary

- Average CLI Cold: 1018ms
- Average CLI Daemon: 177ms
- **Average Speedup: 5.7x**