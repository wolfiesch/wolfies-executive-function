# Normalized MCP Headline Tables

## Run Metadata
- full_node25: iterations=5 warmup=1 phase_timeout_s=30 call_timeout_s=10 workloads=W0_UNREAD,W1_RECENT,W2_SEARCH,W3_THREAD
- mcp_imessage_node22: iterations=5 warmup=1 phase_timeout_s=30 call_timeout_s=10 workloads=W0_UNREAD,W1_RECENT,W2_SEARCH,W3_THREAD
- imcp_only: iterations=5 warmup=1 phase_timeout_s=30 call_timeout_s=10 workloads=W0_UNREAD,W1_RECENT,W2_SEARCH,W3_THREAD

## Server Summary Table
| server | run | node | init_ok | init_ms | list_ok | list_ms | W0_UNREAD | W1_RECENT | W2_SEARCH | W3_THREAD |
|---|---|---|---|---|---|---|---|---|---|---|
| brew MCP: cardmagic/messages (messages --mcp) | full_node25 | v25.2.1 | True | 1015.1 | True | 0.7 | UNSUPPORTED | 0.443ms (p95 0.443) | 451.363ms (p95 450.935) | 9.472ms (p95 9.498) |
| github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | v25.2.1 | True | 1020.8 | True | 1.4 | 31.289ms (p95 31.565) | 0.346ms (p95 0.396) | UNSUPPORTED | 0.156ms (p95 0.161) |
| github MCP: imessage-mcp-improved (node stdio) | full_node25 | v25.2.1 | True | 1009.2 | True | 1.3 | 30.930ms (p95 36.062) | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED |
| github MCP: imessage-query-fastmcp-mcp-server (uv script) | full_node25 | v25.2.1 | True | 1058.0 | True | 1.9 | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | 2.242ms (p95 2.321) |
| github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio) | full_node25 | v25.2.1 | True | 1045.2 | True | 1.4 | UNSUPPORTED | 1.446ms (p95 1.405) | FAIL (TIMEOUT) | FAIL (TIMEOUT) |
| github MCP: mattt/iMCP (swift stdio proxy) | imcp_only |  | True | 1039.4 | True | 26.5 | UNSUPPORTED | 33.673ms (p95 35.672) | 34.414ms (p95 35.081) | UNSUPPORTED |
| github MCP: mcp-imessage (node stdio) | mcp_imessage_node22 | v22.21.1 | True | 1026.4 | True | 2.5 | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | 1.032ms (p95 1.192) |
| github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | v25.2.1 | True | 1016.9 | True | 3.8 | 673.884ms (p95 676.554) | 0.349ms (p95 0.407) | 308.525ms (p95 339.984) | 0.176ms (p95 0.198) |
| github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | v25.2.1 | True | 1019.6 | True | 1.8 | UNSUPPORTED | 9.271ms (p95 9.358) | 23.254ms (p95 23.822) | 18.618ms (p95 18.843) |

## Tool Mapping Table
| server | run | workload | tool | status | ok | mean_ms | p95_ms | error | notes |
|---|---|---|---|---|---|---|---|---|---|
| brew MCP: cardmagic/messages (messages --mcp) | full_node25 | W0_UNREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| brew MCP: cardmagic/messages (messages --mcp) | full_node25 | W1_RECENT | recent_messages | ok | 5/5 | 0.443 | 0.443 |  |  |
| brew MCP: cardmagic/messages (messages --mcp) | full_node25 | W2_SEARCH | search_messages | ok | 5/5 | 451.363 | 450.935 |  |  |
| brew MCP: cardmagic/messages (messages --mcp) | full_node25 | W3_THREAD | get_thread | ok | 5/5 | 9.472 | 9.498 |  |  |
| github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | W0_UNREAD | photon_read_messages | ok | 5/5 | 31.289 | 31.565 |  |  |
| github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | W1_RECENT | photon_get_conversations | ok | 5/5 | 0.346 | 0.396 |  |  |
| github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | W2_SEARCH |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | W3_THREAD | photon_read_messages | ok | 5/5 | 0.156 | 0.161 |  |  |
| github MCP: imessage-mcp-improved (node stdio) | full_node25 | W0_UNREAD | get_unread_imessages | ok | 5/5 | 30.930 | 36.062 |  |  |
| github MCP: imessage-mcp-improved (node stdio) | full_node25 | W1_RECENT |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: imessage-mcp-improved (node stdio) | full_node25 | W2_SEARCH |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: imessage-mcp-improved (node stdio) | full_node25 | W3_THREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: imessage-query-fastmcp-mcp-server (uv script) | full_node25 | W0_UNREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: imessage-query-fastmcp-mcp-server (uv script) | full_node25 | W1_RECENT |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: imessage-query-fastmcp-mcp-server (uv script) | full_node25 | W2_SEARCH |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: imessage-query-fastmcp-mcp-server (uv script) | full_node25 | W3_THREAD | get_chat_transcript | ok | 5/5 | 2.242 | 2.321 |  |  |
| github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio) | full_node25 | W0_UNREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio) | full_node25 | W1_RECENT | get_recent_messages | ok | 5/5 | 1.446 | 1.405 |  |  |
| github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio) | full_node25 | W2_SEARCH | search_messages | fail | 0/5 |  |  | TIMEOUT |  |
| github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio) | full_node25 | W3_THREAD | get_conversation_messages | fail | 0/5 |  |  | TIMEOUT |  |
| github MCP: mattt/iMCP (swift stdio proxy) | imcp_only | W0_UNREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: mattt/iMCP (swift stdio proxy) | imcp_only | W1_RECENT | messages_fetch | ok | 5/5 | 33.673 | 35.672 |  |  |
| github MCP: mattt/iMCP (swift stdio proxy) | imcp_only | W2_SEARCH | messages_fetch | ok | 5/5 | 34.414 | 35.081 |  |  |
| github MCP: mattt/iMCP (swift stdio proxy) | imcp_only | W3_THREAD | messages_fetch | unsupported | 0/0 |  |  |  | target selection returned no candidate |
| github MCP: mcp-imessage (node stdio) | mcp_imessage_node22 | W0_UNREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: mcp-imessage (node stdio) | mcp_imessage_node22 | W1_RECENT |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: mcp-imessage (node stdio) | mcp_imessage_node22 | W2_SEARCH |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: mcp-imessage (node stdio) | mcp_imessage_node22 | W3_THREAD | get-recent-chat-messages | ok | 5/5 | 1.032 | 1.192 |  |  |
| github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | W0_UNREAD | get-unread-messages | ok | 5/5 | 673.884 | 676.554 |  |  |
| github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | W1_RECENT | get-messages | ok | 5/5 | 0.349 | 0.407 |  |  |
| github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | W2_SEARCH | search-messages | ok | 5/5 | 308.525 | 339.984 |  |  |
| github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | W3_THREAD | get-conversation | ok | 5/5 | 0.176 | 0.198 |  |  |
| github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | W0_UNREAD |  | unsupported | 0/0 |  |  |  | unsupported workload (no tool mapping) |
| github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | W1_RECENT | get_recent_messages | ok | 5/5 | 9.271 | 9.358 |  |  |
| github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | W2_SEARCH | search_messages | ok | 5/5 | 23.254 | 23.822 |  |  |
| github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | W3_THREAD | get_messages_from_chat | ok | 5/5 | 18.618 | 18.843 |  |  |

## Workload Rankings (mean_ms, ok only)

### W0_UNREAD
| rank | server | run | node | mean_ms | p95_ms | tool |
|---|---|---|---|---|---|---|
| 1 | github MCP: imessage-mcp-improved (node stdio) | full_node25 | v25.2.1 | 30.930 | 36.062 | get_unread_imessages |
| 2 | github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | v25.2.1 | 31.289 | 31.565 | photon_read_messages |
| 3 | github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | v25.2.1 | 673.884 | 676.554 | get-unread-messages |

### W1_RECENT
| rank | server | run | node | mean_ms | p95_ms | tool |
|---|---|---|---|---|---|---|
| 1 | github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | v25.2.1 | 0.346 | 0.396 | photon_get_conversations |
| 2 | github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | v25.2.1 | 0.349 | 0.407 | get-messages |
| 3 | brew MCP: cardmagic/messages (messages --mcp) | full_node25 | v25.2.1 | 0.443 | 0.443 | recent_messages |
| 4 | github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio) | full_node25 | v25.2.1 | 1.446 | 1.405 | get_recent_messages |
| 5 | github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | v25.2.1 | 9.271 | 9.358 | get_recent_messages |
| 6 | github MCP: mattt/iMCP (swift stdio proxy) | imcp_only |  | 33.673 | 35.672 | messages_fetch |

### W2_SEARCH
| rank | server | run | node | mean_ms | p95_ms | tool |
|---|---|---|---|---|---|---|
| 1 | github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | v25.2.1 | 23.254 | 23.822 | search_messages |
| 2 | github MCP: mattt/iMCP (swift stdio proxy) | imcp_only |  | 34.414 | 35.081 | messages_fetch |
| 3 | github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | v25.2.1 | 308.525 | 339.984 | search-messages |
| 4 | brew MCP: cardmagic/messages (messages --mcp) | full_node25 | v25.2.1 | 451.363 | 450.935 | search_messages |

### W3_THREAD
| rank | server | run | node | mean_ms | p95_ms | tool |
|---|---|---|---|---|---|---|
| 1 | github MCP: TextFly/photon-imsg-mcp (node stdio) | full_node25 | v25.2.1 | 0.156 | 0.161 | photon_read_messages |
| 2 | github MCP: sameelarif/imessage-mcp (node tsx) | full_node25 | v25.2.1 | 0.176 | 0.198 | get-conversation |
| 3 | github MCP: mcp-imessage (node stdio) | mcp_imessage_node22 | v22.21.1 | 1.032 | 1.192 | get-recent-chat-messages |
| 4 | github MCP: imessage-query-fastmcp-mcp-server (uv script) | full_node25 | v25.2.1 | 2.242 | 2.321 | get_chat_transcript |
| 5 | brew MCP: cardmagic/messages (messages --mcp) | full_node25 | v25.2.1 | 9.472 | 9.498 | get_thread |
| 6 | github MCP: wyattjoh/imessage-mcp (deno stdio) | full_node25 | v25.2.1 | 18.618 | 18.843 | get_messages_from_chat |