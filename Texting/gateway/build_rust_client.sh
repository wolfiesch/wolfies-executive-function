#!/usr/bin/env bash
# Build the Rust daemon client and place it in the gateway directory.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRATE_DIR="$SCRIPT_DIR/rust_client"
BINARY_NAME="wolfies-daemon-client"

echo "Building Rust daemon client..."
cd "$CRATE_DIR"

# Build release binary with optimizations
cargo build --release

# Copy binary to gateway directory
cp "target/release/$BINARY_NAME" "$SCRIPT_DIR/"

# Make executable (should already be, but ensure)
chmod +x "$SCRIPT_DIR/$BINARY_NAME"

echo ""
echo "Build complete!"
echo "Binary: $SCRIPT_DIR/$BINARY_NAME"
echo "Size: $(ls -lh "$SCRIPT_DIR/$BINARY_NAME" | awk '{print $5}')"
echo ""
echo "Test with:"
echo "  $SCRIPT_DIR/$BINARY_NAME health"
echo "  $SCRIPT_DIR/$BINARY_NAME --help"
