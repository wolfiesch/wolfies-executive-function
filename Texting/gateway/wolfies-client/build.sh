#!/usr/bin/env bash
# Build the wolfies-client workspace and copy binary to gateway directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Building wolfies-client workspace..."
cargo build --release

# Copy binary to gateway directory for backwards compatibility
cp target/release/wolfies-daemon-client "$SCRIPT_DIR/../wolfies-daemon-client"

echo ""
echo "Build complete!"
echo "Binary at: $SCRIPT_DIR/../wolfies-daemon-client"
ls -lh "$SCRIPT_DIR/../wolfies-daemon-client"
