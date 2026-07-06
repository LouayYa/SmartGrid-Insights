#!/usr/bin/env sh
# Build all service images and load them into a kind cluster.
#
#   kind create cluster --name smartgrid
#   sh k8s/kind-build-load.sh
#   kubectl apply -k k8s/
#
# Run from the repo root or the k8s/ directory.
set -e

cd "$(dirname "$0")/.."

CLUSTER="${KIND_CLUSTER:-smartgrid}"

docker build -t smartgrid/meter:local      ./smartgrid-meter-registration/meter-registration-service
docker build -t smartgrid/ingestion:local  ./smart-data-ingestion/Cloud_Project_Saif
docker build -t smartgrid/collection:local ./smartgrid-data-collection
docker build -t smartgrid/analysis:local   ./smartgrid-data-analysis
docker build -t smartgrid/ui:local         ./smartgrid-UI/smart-grid-webui

kind load docker-image --name "$CLUSTER" \
  smartgrid/meter:local \
  smartgrid/ingestion:local \
  smartgrid/collection:local \
  smartgrid/analysis:local \
  smartgrid/ui:local

echo "Images loaded into kind cluster '$CLUSTER'. Now: kubectl apply -k k8s/"
