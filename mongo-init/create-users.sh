#!/usr/bin/env bash
set -euo pipefail
# Solo se ejecuta cuando el volumen MongoDB es nuevo.
for name in inventory orders clients payments; do
  export FLOR_DB="flor_${name}"
  export FLOR_USER="${name}_user"
  export FLOR_PASSWORD
  FLOR_PASSWORD="$(cat "/run/secrets/mongo-${name}-password")"
  mongosh --quiet --username "$MONGO_INITDB_ROOT_USERNAME" \
    --password "$(cat /run/secrets/mongo-root-password)" --authenticationDatabase admin \
    --eval 'db.getSiblingDB(process.env.FLOR_DB).createUser({user:process.env.FLOR_USER,pwd:process.env.FLOR_PASSWORD,roles:[{role:"readWrite",db:process.env.FLOR_DB}]})'
  unset FLOR_PASSWORD
done
touch /data/db/flor_initialized
