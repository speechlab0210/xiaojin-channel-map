#!/bin/bash
# Run the full pipeline on whatever captions are in captions/
set -e
export PYTHONIOENCODING=utf-8

cd "$(dirname "$0")/.."

echo "=== Stage 1a: extract candidates from captions/ ==="
python scripts/extract_ref_candidates.py

echo ""
echo "=== Stage 1b: classify candidates ==="
python scripts/classify_refs.py

echo ""
echo "=== Stage 2: resolve targets ==="
python scripts/resolve_targets.py

echo ""
echo "=== Stage 3: build graph data ==="
python scripts/build_graph_data.py

# Copy graph.json into site/
cp data/graph.json site/graph.json
echo ""
echo "=== Done. Site data updated. ==="
echo "Open site/index.html in a browser."
