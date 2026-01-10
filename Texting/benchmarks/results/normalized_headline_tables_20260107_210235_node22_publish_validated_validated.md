# Normalized MCP Headline Tables (Validated)

## Run Metadata
- 20260107_210235_node22_publish_validated: iterations=20 warmup=1 phase_timeout_s=40 call_timeout_s=30 workloads=W0_UNREAD,W1_RECENT,W2_SEARCH,W3_THREAD
- strict_validity=True min_bytes={'W0_UNREAD': 150, 'W1_RECENT': 200, 'W2_SEARCH': 200, 'W3_THREAD': 150} min_items={'W0_UNREAD': 0, 'W1_RECENT': 1, 'W2_SEARCH': 1, 'W3_THREAD': 1}

## Server Summary Table
|server|run|node|init_ok|init_ms|list_ok|list_ms|W0_UNREAD|W1_RECENT|W2_SEARCH|W3_THREAD|
|---|---|---|---|---|---|---|---|---|---|---|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_210235_node22_publish_validated|v22.21.1|True|1019.275|True|2.290|UNSUPPORTED|OK_EMPTY 1.653ms (p95 2.202)|OK_EMPTY 1.284ms (p95 1.688)|OK_EMPTY 1.134ms (p95 1.367)|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|v22.21.1|True|1026.583|True|2.054|UNSUPPORTED|8.990ms (p95 9.316)|26.035ms (p95 30.852)|1.781ms (p95 2.105)|
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|v22.21.1|True|1018.177|True|1.250|UNSUPPORTED|2.473ms (p95 2.711)|1666.787ms (p95 3406.559)|1.388ms (p95 1.594)|
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|v22.21.1|True|1072.889|True|16.512|UNSUPPORTED|31.650ms (p95 36.185)|28.553ms (p95 34.338)|FAIL|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_210235_node22_publish_validated|v22.21.1|True|1042.420|True|1.663|OK_EMPTY 34.156ms (p95 34.957)|0.308ms (p95 0.424)|UNSUPPORTED|OK_EMPTY 0.148ms (p95 0.183)|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|v22.21.1|True|1018.519|True|5.864|723.645ms (p95 834.729)|0.204ms (p95 0.347)|OK_EMPTY 300.727ms (p95 388.902)|FAIL|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_210235_node22_publish_validated|v22.21.1|True|1051.958|True|2.347|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|FAIL|
|github MCP: mcp-imessage (node stdio)|20260107_210235_node22_publish_validated|v22.21.1|True|1018.127|True|1.700|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|FAIL|
|github MCP: imessage-mcp-improved (node stdio)|20260107_210235_node22_publish_validated|v22.21.1|True|1058.012|True|1.690|23.882ms (p95 29.754)|UNSUPPORTED|UNSUPPORTED|UNSUPPORTED|

## Tool Mapping Table
|server|run|workload|tool|status|ok|mean_ms|p95_ms|error|notes|
|---|---|---|---|---|---|---|---|---|---|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_210235_node22_publish_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_210235_node22_publish_validated|W1_RECENT|recent_messages|ok_empty|0/20|1.653|2.202||suspicious: identical payload across workloads W1_RECENT, W2_SEARCH, W3_THREAD; raw_ok=20/20|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_210235_node22_publish_validated|W2_SEARCH|search_messages|ok_empty|0/20|1.284|1.688||suspicious: identical payload across workloads W1_RECENT, W2_SEARCH, W3_THREAD; raw_ok=20/20|
|brew MCP: cardmagic/messages (messages --mcp)|20260107_210235_node22_publish_validated|W3_THREAD|get_thread|ok_empty|0/20|1.134|1.367||suspicious: identical payload across workloads W1_RECENT, W2_SEARCH, W3_THREAD; raw_ok=20/20|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|W1_RECENT|get_recent_messages|ok_valid|20/20|8.990|9.316|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|W2_SEARCH|search_messages|ok_valid|20/20|26.035|30.852|||
|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|W3_THREAD|get_messages_from_chat|ok_valid|20/20|1.781|2.105|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|W1_RECENT|get_recent_messages|ok_valid|20/20|2.473|2.711|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|W2_SEARCH|search_messages|ok_valid|20/20|1666.787|3406.559|||
|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|W3_THREAD|get_conversation_messages|ok_valid|20/20|1.388|1.594|||
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|W1_RECENT|messages_fetch|ok_valid|20/20|31.650|36.185|||
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|W2_SEARCH|messages_fetch|ok_valid|20/20|28.553|34.338|||
|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|W3_THREAD|messages_fetch|fail|0/0||||target selection returned no candidate|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_210235_node22_publish_validated|W0_UNREAD|photon_read_messages|ok_empty|0/20|34.156|34.957||suspicious: identical payload across workloads W0_UNREAD, W3_THREAD; raw_ok=20/20|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_210235_node22_publish_validated|W1_RECENT|photon_get_conversations|ok_valid|20/20|0.308|0.424|||
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_210235_node22_publish_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_210235_node22_publish_validated|W3_THREAD|photon_read_messages|ok_empty|0/20|0.148|0.183||suspicious: identical payload across workloads W0_UNREAD, W3_THREAD; raw_ok=20/20|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|W0_UNREAD|get-unread-messages|ok_valid|20/20|723.645|834.729|||
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|W1_RECENT|get-messages|ok_valid|20/20|0.204|0.347|||
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|W2_SEARCH|search-messages|ok_empty|0/20|300.727|388.902||raw_ok=20/20|
|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|W3_THREAD|get-conversation|fail|0/0||||target selection returned no candidate|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_210235_node22_publish_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_210235_node22_publish_validated|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_210235_node22_publish_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-query-fastmcp-mcp-server (uv script)|20260107_210235_node22_publish_validated|W3_THREAD|get_chat_transcript|fail|0/0||||missing target selector for thread workload|
|github MCP: mcp-imessage (node stdio)|20260107_210235_node22_publish_validated|W0_UNREAD||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|20260107_210235_node22_publish_validated|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|20260107_210235_node22_publish_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: mcp-imessage (node stdio)|20260107_210235_node22_publish_validated|W3_THREAD|get-recent-chat-messages|fail|0/0||||missing target selector for thread workload|
|github MCP: imessage-mcp-improved (node stdio)|20260107_210235_node22_publish_validated|W0_UNREAD|get_unread_imessages|ok_valid|20/20|23.882|29.754|||
|github MCP: imessage-mcp-improved (node stdio)|20260107_210235_node22_publish_validated|W1_RECENT||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-mcp-improved (node stdio)|20260107_210235_node22_publish_validated|W2_SEARCH||unsupported|0/0||||unsupported workload (no tool mapping)|
|github MCP: imessage-mcp-improved (node stdio)|20260107_210235_node22_publish_validated|W3_THREAD||unsupported|0/0||||unsupported workload (no tool mapping)|

## Workload Rankings (ok_valid only)
Rankings exclude ok_empty.

### W0_UNREAD
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: imessage-mcp-improved (node stdio)|20260107_210235_node22_publish_validated|v22.21.1|23.882|29.754|get_unread_imessages|
|2|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|v22.21.1|723.645|834.729|get-unread-messages|

### W1_RECENT
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: sameelarif/imessage-mcp (node tsx)|20260107_210235_node22_publish_validated|v22.21.1|0.204|0.347|get-messages|
|2|github MCP: TextFly/photon-imsg-mcp (node stdio)|20260107_210235_node22_publish_validated|v22.21.1|0.308|0.424|photon_get_conversations|
|3|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|v22.21.1|2.473|2.711|get_recent_messages|
|4|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|v22.21.1|8.990|9.316|get_recent_messages|
|5|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|v22.21.1|31.650|36.185|messages_fetch|

### W2_SEARCH
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|v22.21.1|26.035|30.852|search_messages|
|2|github MCP: mattt/iMCP (swift stdio proxy)|20260107_210235_node22_publish_validated|v22.21.1|28.553|34.338|messages_fetch|
|3|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|v22.21.1|1666.787|3406.559|search_messages|

### W3_THREAD
|rank|server|run|node|mean_ms|p95_ms|tool|
|---|---|---|---|---|---|---|
|1|github MCP: jonmmease/jons-mcp-imessage (python fastmcp stdio)|20260107_210235_node22_publish_validated|v22.21.1|1.388|1.594|get_conversation_messages|
|2|github MCP: wyattjoh/imessage-mcp (deno stdio)|20260107_210235_node22_publish_validated|v22.21.1|1.781|2.105|get_messages_from_chat|
