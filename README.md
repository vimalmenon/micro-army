# 🪖 micro-army

Microservices army — backend services running on the homelab k3s cluster.

## Services

| Service | Description | Stack |
|---|---|---|
| **dynamo-svc** | Amazon DynamoDB gateway | FastAPI + boto3 |

## Structure

```
micro-army/
├── services/
│   └── <service-name>/
│       ├── src/          # Python source code
│       ├── Dockerfile
│       └── requirements.txt
└── common/               # Shared utilities (future)
```

Each service is deployed on the cluster via ArgoCD from the [homelab-army](https://github.com/vimalmenon/homelab-army) repo.
