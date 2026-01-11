# Normalized MCP Headline Tables (Node 22 only, timeout30)

## Run Metadata
- full_node22_timeout30: iterations=5 warmup=1 phase_timeout_s=40 call_timeout_s=30 workloads=W0_UNREAD,W1_RECENT,W2_SEARCH,W3_THREAD

## Server Summary Table
|server|run|node|init_ok|init_ms|list_ok|list_ms|W0_UNREAD|W1_RECENT|W2_SEARCH|W3_THREAD|
|---|---|---|---|---|---|---|---|---|---|---|
|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|v22.21.1|True|1021.2|True|2.3|UNSUPPORTED|2.117ms (p95 2.121)|1.460ms (p95 1.536)|1.216ms (p95 1.250)|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|v22.21.1|True|1059.1|True|2.5|UNSUPPORTED|10.205ms (p95 10.866)|30.057ms (p95 33.061)|0.272ms (p95 0.324)|
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|full_node22_timeout30|v22.21.1|True|1029.5|True|1.3|UNSUPPORTED|1.565ms (p95 1.561)|FAIL (TIMEOUT)|FAIL (TIMEOUT)|
|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|v22.21.1|True|1022.4|True|22.3|UNSUPPORTED|33.020ms (p95 34.632)|30.265ms (p95 34.937)|10.629ms (p95 11.345)|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|v22.21.1|True|1032.3|True|1.5|36.226ms (p95 39.630)|0.370ms (p95 0.370)|UNSUPPORTED|0.132ms (p95 0.131)|
|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|v22.21.1|True|1050.0|True|4.5|715.344ms (p95 757.500)|0.287ms (p95 0.359)|283.741ms (p95 289.912)|0.172ms (p95 0.197)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|full_node22_timeout30|v22.21.1|True|1055.0|True|1.9|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|2.406ms (p95 2.593)|
|github MCP: mcp-imessage (node stdio)|full_node22_timeout30|v22.21.1|True|1055.0|True|0.9|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|0.546ms (p95 0.607)|
|github MCP: imessage-mcp-improved (node stdio)|full_node22_timeout30|v22.21.1|True|1029.0|True|1.9|21.434ms (p95 22.138)|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|

## Tool Mapping Table
|server|run|workload|tool|status|ok|mean_ms|p95_ms|error|notes|
|---|---|---|---|---|---|---|---|---|---|
|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|W1_RECENT|recent_messages|ok|5/5|2.117|2.121|||
|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|W2_SEARCH|search_messages|ok|5/5|1.460|1.536|||
|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|W3_THREAD|get_thread|ok|5/5|1.216|1.250|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|W1_RECENT|get_recent_messages|ok|5/5|10.205|10.866|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|W2_SEARCH|search_messages|ok|5/5|30.057|33.061|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|W3_THREAD|get_messages_from_chat|ok|5/5|0.272|0.324|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|full_node22_timeout30|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|full_node22_timeout30|W1_RECENT|get_recent_messages|ok|5/5|1.565|1.561|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|full_node22_timeout30|W2_SEARCH|search_messages|fail|0/5|||TIMEOUT||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|full_node22_timeout30|W3_THREAD|get_conversation_messages|fail|0/5|||TIMEOUT||
|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|W1_RECENT|messages_fetch|ok|5/5|33.020|34.632|||
|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|W2_SEARCH|messages_fetch|ok|5/5|30.265|34.937|||
|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|W3_THREAD|messages_fetch|ok|5/5|10.629|11.345|||
|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|W0_UNREAD|photon_read_messages|ok|5/5|36.226|39.630|||
|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|W1_RECENT|photon_get_conversations|ok|5/5|0.370|0.370|||
|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|W3_THREAD|photon_read_messages|ok|5/5|0.132|0.131|||
|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|W0_UNREAD|get-unread-messages|ok|5/5|715.344|757.500|||
|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|W1_RECENT|get-messages|ok|5/5|0.287|0.359|||
|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|W2_SEARCH|search-messages|ok|5/5|283.741|289.912|||
|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|W3_THREAD|get-conversation|ok|5/5|0.172|0.197|||
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|full_node22_timeout30|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|full_node22_timeout30|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|full_node22_timeout30|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|full_node22_timeout30|W3_THREAD|get_chat_transcript|ok|5/5|2.406|2.593|||
|github MCP: mcp-imessage (node stdio)|full_node22_timeout30|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|full_node22_timeout30|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|full_node22_timeout30|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|full_node22_timeout30|W3_THREAD|get-recent-chat-messages|ok|5/5|0.546|0.607|||
|github MCP: imessage-mcp-improved (node stdio)|full_node22_timeout30|W0_UNREAD|get_unread_imessages|ok|5/5|21.434|22.138|||
|github MCP: imessage-mcp-improved (node stdio)|full_node22_timeout30|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-mcp-improved (node stdio)|full_node22_timeout30|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-mcp-improved (node stdio)|full_node22_timeout30|W3_THREAD||unsupported|0/0||||unsupported workload (no tool mapping)|

## Workload Rankings (mean_ms, ok only)

### W0_UNREAD
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: imessage-mcp-improved (node stdio)|full_node22_timeout30|v22.21.1|21.434|22.138|get_unread_imessages|
|2|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|v22.21.1|36.226|39.630|photon_read_messages|
|3|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|v22.21.1|715.344|757.500|get-unread-messages|

### W1_RECENT
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|v22.21.1|0.287|0.359|get-messages|
|2|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|v22.21.1|0.370|0.370|photon_get_conversations|
|3|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|full_node22_timeout30|v22.21.1|1.565|1.561|get_recent_messages|
|4|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|v22.21.1|2.117|2.121|recent_messages|
|5|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|v22.21.1|10.205|10.866|get_recent_messages|
|6|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|v22.21.1|33.020|34.632|messages_fetch|

### W2_SEARCH
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|v22.21.1|1.460|1.536|search_messages|
|2|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|v22.21.1|30.057|33.061|search_messages|
|3|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|v22.21.1|30.265|34.937|messages_fetch|
|4|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|v22.21.1|283.741|289.912|search-messages|

### W3_THREAD
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: TextFly/photon-imsg-mcp (node stdio)|full_node22_timeout30|v22.21.1|0.132|0.131|photon_read_messages|
|2|github MCP: sameelarif/imessage-mcp (node tsx)|full_node22_timeout30|v22.21.1|0.172|0.197|get-conversation|
|3|github MCP: wyattjoh/imessage-mcp (deno stdio)|full_node22_timeout30|v22.21.1|0.272|0.324|get_messages_from_chat|
|4|github MCP: mcp-imessage (node stdio)|full_node22_timeout30|v22.21.1|0.546|0.607|get-recent-chat-messages|
|5|brew MCP: cardmagic/messages (messages --mcp)|full_node22_timeout30|v22.21.1|1.216|1.250|get_thread|
|6|github MCP: imessage-query-fastmcp-mcp-server (uv script)|full_node22_timeout30|v22.21.1|2.406|2.593|get_chat_transcript|
|7|github MCP: mattt/iMCP (swift stdio proxy)|full_node22_timeout30|v22.21.1|10.629|11.345|messages_fetch|
