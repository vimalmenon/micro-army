# Hestia — Admin Backend API

**Goddess of the Hearth — the warm center of the home**

Hestia (Ἑστία) was the goddess of the hearth, home, and domestic life. Every household and city maintained her sacred flame — the central, stabilizing presence around which everything revolved.

**Why Hestia?**

This microservice is the backend API for the admin dashboard. It proxies requests to Clio (data), Pythia (leads), and other services, providing a single stable access point. Like Hestia's hearth at the center of the home, this service is the warm, reliable middle layer that ties the admin experience together.

**Domain:** Admin API — proxies Clio & Pythia for dashboard
**Stack:** FastAPI + httpx
**Dependencies:** Clio (DynamoDB), Pythia (leads)
**Auth:** API key (consumed by Helios)
