#!/usr/bin/env bash
set -euo pipefail
export FLOR_DB='flor_analytics' FLOR_USER='analytics_user'
export FLOR_PASSWORD="$(cat /run/secrets/mongo-analytics-password)"
mongosh --quiet --host mongo -u root -p "$(cat /run/secrets/mongo-root-password)" --authenticationDatabase admin \
  --eval 'const target=db.getSiblingDB(process.env.FLOR_DB); if (!target.getUser(process.env.FLOR_USER)) {target.createUser({user:process.env.FLOR_USER, pwd:process.env.FLOR_PASSWORD, roles:[{role:"readWrite",db:process.env.FLOR_DB}]}); print("Usuario Analytics creado") } else {print("Usuario Analytics ya existe")}'
unset FLOR_PASSWORD
