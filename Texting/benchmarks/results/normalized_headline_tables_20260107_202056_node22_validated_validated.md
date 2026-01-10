# Normalized MCP Headline Tables (Validated)

## Run Metadata
- 20260107_202056_node22_validated: iterations=5 warmup=1 phase_timeout_s=40 call_timeout_s=30 workloads=W0_UNREAD,W1_RECENT,W2_SEARCH,W3_THREAD
- strict_validity=True min_bytes={'W0_UNREAD': 150, 'W1_RECENT': 200, 'W2_SEARCH': 200, 'W3_THREAD': 150} min_items={'W0_UNREAD': 0, 'W1_RECENT': 1, 'W2_SEARCH': 1, 'W3_THREAD': 1}

## Server Summary Table
|server|run|node|init_ok|init_ms|list_ok|list_ms|W0_UNREAD|W1_RECENT|W2_SEARCH|W3_THREAD|
|---|---|---|---|---|---|---|---|---|---|---|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_202056_node22_validated|v22.21.1|True|1021.508|True|1.524|UNSUPPORTED|OK_EMPTY 1.900ms (p95 1.995)|OK_EMPTY 1.506ms (p95 1.468)|OK_EMPTY 1.365ms (p95 1.584)|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|v22.21.1|True|1056.552|True|3.405|UNSUPPORTED|10.019ms (p95 10.354)|26.780ms (p95 29.757)|1.725ms (p95 1.766)|
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_202056_node22_validated|v22.21.1|True|1024.047|True|1.359|UNSUPPORTED|1.594ms (p95 1.648)|FAIL (TIMEOUT)|FAIL|
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|v22.21.1|True|2370.655|True|15.286|UNSUPPORTED|33.329ms (p95 35.026)|30.771ms (p95 32.522)|FAIL|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_202056_node22_validated|v22.21.1|True|1024.535|True|3.010|OK_EMPTY 32.711ms (p95 32.082)|0.317ms (p95 0.356)|UNSUPPORTED|OK_EMPTY 0.155ms (p95 0.178)|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_202056_node22_validated|v22.21.1|True|1053.547|True|9.865|832.115ms (p95 906.327)|OK_EMPTY 0.276ms (p95 0.350)|OK_EMPTY 277.209ms (p95 283.483)|FAIL|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_202056_node22_validated|v22.21.1|True|1053.588|True|3.307|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|FAIL|
|github MCP: mcp-imessage (node stdio)|20260107_202056_node22_validated|v22.21.1|True|1024.605|True|2.440|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|FAIL|
|github MCP: imessage-mcp-improved (node stdio)|20260107_202056_node22_validated|v22.21.1|True|1032.212|True|3.401|30.085ms (p95 30.528)|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|

## Tool Mapping Table
|server|run|workload|tool|status|ok|mean_ms|p95_ms|error|notes|
|---|---|---|---|---|---|---|---|---|---|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_202056_node22_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_202056_node22_validated|W1_RECENT|recent_messages|ok_empty|0/5|1.900|1.995||suspicious: identical payload across workloads W1_RECENT, W2_SEARCH, W3_THREAD; raw_ok=5/5|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_202056_node22_validated|W2_SEARCH|search_messages|ok_empty|0/5|1.506|1.468||suspicious: identical payload across workloads W1_RECENT, W2_SEARCH, W3_THREAD; raw_ok=5/5|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_202056_node22_validated|W3_THREAD|get_thread|ok_empty|0/5|1.365|1.584||suspicious: identical payload across workloads W1_RECENT, W2_SEARCH, W3_THREAD; raw_ok=5/5|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|W1_RECENT|get_recent_messages|ok_valid|5/5|10.019|10.354|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|W2_SEARCH|search_messages|ok_valid|5/5|26.780|29.757|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|W3_THREAD|get_messages_from_chat|ok_valid|5/5|1.725|1.766|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_202056_node22_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_202056_node22_validated|W1_RECENT|get_recent_messages|ok_valid|5/5|1.594|1.648|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_202056_node22_validated|W2_SEARCH|search_messages|fail_timeout|0/5|||TIMEOUT||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_202056_node22_validated|W3_THREAD|get_conversation_messages|fail|0/0||||target selection failed: TIMEOUT|
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|W1_RECENT|messages_fetch|ok_valid|5/5|33.329|35.026|||
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|W2_SEARCH|messages_fetch|ok_valid|5/5|30.771|32.522|||
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|W3_THREAD|messages_fetch|fail|0/0||||target selection returned no candidate|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_202056_node22_validated|W0_UNREAD|photon_read_messages|ok_empty|0/5|32.711|32.082||suspicious: identical payload across workloads W0_UNREAD, W3_THREAD; raw_ok=5/5|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_202056_node22_validated|W1_RECENT|photon_get_conversations|ok_valid|5/5|0.317|0.356|||
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_202056_node22_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_202056_node22_validated|W3_THREAD|photon_read_messages|ok_empty|0/5|0.155|0.178||suspicious: identical payload across workloads W0_UNREAD, W3_THREAD; raw_ok=5/5|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_202056_node22_validated|W0_UNREAD|get-unread-messages|ok_valid|5/5|832.115|906.327|||
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_202056_node22_validated|W1_RECENT|get-messages|ok_empty|0/5|0.276|0.350||raw_ok=5/5|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_202056_node22_validated|W2_SEARCH|search-messages|ok_empty|0/5|277.209|283.483||raw_ok=5/5|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_202056_node22_validated|W3_THREAD|get-conversation|fail|0/0||||target selection returned no candidate|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_202056_node22_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_202056_node22_validated|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_202056_node22_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_202056_node22_validated|W3_THREAD|get_chat_transcript|fail|0/0||||missing target selector for thread workload|
|github MCP: mcp-imessage (node stdio)|20260107_202056_node22_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|20260107_202056_node22_validated|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|20260107_202056_node22_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|20260107_202056_node22_validated|W3_THREAD|get-recent-chat-messages|fail|0/0||||missing target selector for thread workload|
|github MCP: imessage-mcp-improved (node stdio)|20260107_202056_node22_validated|W0_UNREAD|get_unread_imessages|ok_valid|5/5|30.085|30.528|||
|github MCP: imessage-mcp-improved (node stdio)|20260107_202056_node22_validated|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-mcp-improved (node stdio)|20260107_202056_node22_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-mcp-improved (node stdio)|20260107_202056_node22_validated|W3_THREAD||unsupported|0/0||||unsupported workload (no tool mapping)|

## Workload Rankings (ok_valid only)
Rankings exclude ok_empty.

### W0_UNREAD
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: imessage-mcp-improved (node stdio)|20260107_202056_node22_validated|v22.21.1|30.085|30.528|get_unread_imessages|
|2|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_202056_node22_validated|v22.21.1|832.115|906.327|get-unread-messages|

### W1_RECENT
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_202056_node22_validated|v22.21.1|0.317|0.356|photon_get_conversations|
|2|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_202056_node22_validated|v22.21.1|1.594|1.648|get_recent_messages|
|3|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|v22.21.1|10.019|10.354|get_recent_messages|
|4|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|v22.21.1|33.329|35.026|messages_fetch|

### W2_SEARCH
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|v22.21.1|26.780|29.757|search_messages|
|2|github MCP: mattt/iMCP (swift stdio proxy)|20260107_202056_node22_validated|v22.21.1|30.771|32.522|messages_fetch|

### W3_THREAD
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_202056_node22_validated|v22.21.1|1.725|1.766|get_messages_from_chat|
