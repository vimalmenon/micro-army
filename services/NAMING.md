# Micro-Army — Olympus Cluster

## Greek Mythology Naming Convention

All microservices in the Complete Automate ecosystem follow a **Greek mythology** naming theme. The k3s cluster is named **Olympus** — home of the gods.

Each service is named after a Greek god, muse, or mythological figure whose domain mirrors the service's function.

| Service Name | God/Muse | Mythological Role | Real-World Function |
|:--|:--|:--|:--|
| **Clio** | Κλειώ (Clio) | Muse of History — keeper of records | DynamoDB persistence layer |
| **Atlas** | Ἄτλας (Atlas) | Titan who held up the heavens | S3 file storage |
| **Athena** | Ἀθηνᾶ (Athena) | Goddess of Wisdom | Wiki / knowledge base |
| **Orpheus** | Ὀρφεύς (Orpheus) | Musician who could charm all things | YouTube video management |
| **Iris** | Ἶρις (Iris) | Goddess of Messages & Rainbow | Email delivery |
| **Angelos** | Ἄγγελος (Angelos) | Messenger Deity | Contact form API |
| **Arachne** | Ἀράχνη (Arachne) | Weaver turned spider | Cloudflare tunnel sync |
| **Hephaestus** | Ἥφαιστος (Hephaestus) | God of the Forge | MCP-as-a-Service *(planned)* |

### Why?

Greek mythology gives us a **coherent, memorable, and extensible** naming system:

- **Memorable** — a story is easier to remember than a technical description
- **Self-documenting** — the myth hints at the service's purpose
- **Extensible** — there are hundreds of figures; adding new services never runs out of names
- **Fun** — debugging "why is Arachne not weaving?" is more enjoyable than "why did tunnel-sync fail?"

### Internal DNS

Services talk to each other via Kubernetes DNS:
```
<name>.microservices.svc.cluster.local:8000
```
E.g., `clio.microservices.svc.cluster.local:8000`

### Cluster

The k3s cluster itself is named **Olympus**. All microservices run in the `microservices` namespace.

### Source Code

The source lives in two repos:
- **`micro-army`** — service code, Dockerfiles, CI workflows
- **`homelab-army`** — k8s manifests, ArgoCD apps
