import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    dynamo_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "DYNAMO_SVC_URL", "http://clio.microservices.svc.cluster.local:8000"
        )
    )
    iris_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "IRIS_SVC_URL", "http://iris.microservices.svc.cluster.local:8000"
        )
    )
    pythia_svc_url: str = field(
        default_factory=lambda: os.getenv(
            "PYTHIA_SVC_URL", "http://pythia.microservices.svc.cluster.local:8000"
        )
    )
    service_port: int = field(default_factory=lambda: int(os.getenv("SERVICE_PORT", "8000")))


settings = Settings()
