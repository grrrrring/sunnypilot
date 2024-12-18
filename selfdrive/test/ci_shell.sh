#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null && pwd)"
OP_ROOT="$DIR/../../"

if [ -z "$BUILD" ]; then
  docker pull ghcr.io/commaai/openpilot-base:64db514d41eea2ffbed01998708596b7429f1fa5
else
  docker build --cache-from ghcr.io/commaai/openpilot-base:64db514d41eea2ffbed01998708596b7429f1fa5 -t ghcr.io/commaai/openpilot-base:64db514d41eea2ffbed01998708596b7429f1fa5 -f $OP_ROOT/Dockerfile.openpilot_base .
fi

docker run \
       -it \
       --rm \
       --volume $OP_ROOT:$OP_ROOT \
       --workdir $PWD \
       --env PYTHONPATH=$OP_ROOT \
       ghcr.io/commaai/openpilot-base:64db514d41eea2ffbed01998708596b7429f1fa5 \
       /bin/bash
