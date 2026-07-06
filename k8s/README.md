# Running SmartGrid Insights on Kubernetes

The whole platform — five microservices, the Kafka readings consumer, a
single-node KRaft Kafka broker, and Postgres 16 — deploys to any Kubernetes
cluster from the manifests in this directory (plain YAML + kustomize, applied
with `kubectl apply -k`).

Every app container has liveness/readiness probes on `/health`, resource
requests/limits, config via ConfigMap, and the Postgres password via a
Secret. The stateful services run their Alembic migrations on startup, same
as in docker compose.

## Local cluster (kind) — verified

```bash
# 1. Create a cluster (kind: https://kind.sigs.k8s.io)
kind create cluster --name smartgrid

# 2. Build the five service images and load them into the cluster
sh k8s/kind-build-load.sh

# 3. Deploy everything
kubectl apply -k k8s/
kubectl -n smartgrid wait --for=condition=available deployment --all --timeout=300s

# 4. Use it
kubectl -n smartgrid port-forward svc/ui 8004:8004   # UI on http://localhost:8004
```

Seed data the same way as compose: `POST /api/v1/load` on the ingestion
service (port-forward `svc/ingestion 8001:8001`), register a meter in the
UI, trigger a simulation, and watch the consumer logs:
`kubectl -n smartgrid logs deploy/collection-consumer -f`.

Notes:
- The DB-backed services crash-restart a few times on first boot while
  Postgres initialises — Kubernetes has no `depends_on`; the restart policy
  plus readiness probes converge in under a minute. This is the standard
  pattern (an initContainer wait is the alternative).
- Kafka's controller quorum uses `localhost:9093` because a Service exposes
  no endpoints until the pod is Ready — a single-node KRaft bootstrap detail
  (see the comment in `kafka.yaml`).
- Replace the placeholder password in `secret.yaml` (or create the Secret
  out of band) for anything shared.

## Deploying to GCP (documented path — not provisioned, to stay at $0)

The same manifests map to a GKE deployment with managed replacements for
the stateful pieces:

1. **Images → Artifact Registry**
   ```bash
   gcloud artifacts repositories create smartgrid --repository-format=docker --location=europe-west2
   docker tag smartgrid/collection:local europe-west2-docker.pkg.dev/$PROJECT/smartgrid/collection:v1
   docker push europe-west2-docker.pkg.dev/$PROJECT/smartgrid/collection:v1   # etc. for all five
   ```
   Update the `image:` fields (or add a kustomize overlay with `images:` transformers).

2. **Cluster → GKE Autopilot**
   ```bash
   gcloud container clusters create-auto smartgrid --region=europe-west2
   gcloud container clusters get-credentials smartgrid --region=europe-west2
   kubectl apply -k k8s/
   ```

3. **Managed replacements** (recommended over in-cluster StatefulSets):
   - Postgres → **Cloud SQL for PostgreSQL** (point `DATABASE_URL`s at it via the Cloud SQL Auth Proxy sidecar)
   - Kafka → **GCP Managed Service for Apache Kafka** (update `KAFKA_BOOTSTRAP_SERVERS`)
   - Airflow → **Cloud Composer** (upload `airflow/dags/`)
   - Secrets → **Secret Manager** with the Secret Manager CSI driver
   - UI exposure → Service `type: LoadBalancer` or a GKE Ingress + managed cert

4. **Teardown** (this is what costs money if forgotten):
   ```bash
   gcloud container clusters delete smartgrid --region=europe-west2
   ```
