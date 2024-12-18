#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
OP_ROOT="$DIR/../../"

if [ -z "$BUILD" ]; then
  docker pull ghcr.io/commaai/openpilot-base:d40fd1956d5f7ac1e42c40d7e5b1740a528747a2
else
  docker build --cache-from ghcr.io/commaai/openpilot-base:d40fd1956d5f7ac1e42c40d7e5b1740a528747a2 -t ghcr.io/commaai/openpilot-base:d40fd1956d5f7ac1e42c40d7e5b1740a528747a2 -f $OP_ROOT/Dockerfile.openpilot_base .
fi

docker run \
       -it \
       --rm \
       --volume $OP_ROOT:$OP_ROOT \
       --workdir $PWD \
       --env PYTHONPATH=$OP_ROOT \
       ghcr.io/commaai/openpilot-base:d40fd1956d5f7ac1e42c40d7e5b1740a528747a2 \
       /bin/bash
