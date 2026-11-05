"""Plain records for the rows read from SQLite.

They only hold data. The rules live in the domain classes (User, Product, ...);
repository.py converts between the two.
"""
from dataclasses import dataclass, field


@dataclass
class UserRow:
    id: int
    email: str
    role: str
    password_hash: str
    active: bool = True

    @classmethod
    def from_db(cls, r):
        return cls(r["id"], r["email"], r["role"], r["password_hash"], bool(r["active"]))


@dataclass
class MaterialRow:
    material: str
    percent: float
    recycled_share: float
    recyclable: bool
    hazard: bool

    @classmethod
    def from_db(cls, r):
        return cls(r["material"], r["percent"], r["recycled_share"], bool(r["recyclable"]), bool(r["hazard"]))


@dataclass
class QRCodeRow:
    target_url: str
    png_bytes: bytes


@dataclass
class HistoryEventRow:
    """One history entry. It has the same getters as Subsystem 2's LifecycleEvent,
    so Subsystem 2's EventHasher and ChainVerifier check it without any changes."""
    product_uuid: str
    event_type: str
    timestamp: str
    actor_email: str
    actor_role: str
    details: str
    previous_hash: str
    event_hash: str = ""
    id: int | None = None

    @classmethod
    def from_db(cls, r, product_uuid):
        return cls(product_uuid, r["event_type"], r["timestamp"], r["actor_email"], r["actor_role"],
                   r["details"], r["previous_hash"], r["event_hash"], r["id"])

    # ---- LifecycleEvent-compatible getters ----
    def get_event_data(self):
        return {
            "product_uuid": self.product_uuid,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "actor_email": self.actor_email,
            "details": self.details,
            "previous_hash": self.previous_hash,
        }

    def get_previous_hash(self):
        return self.previous_hash

    def get_event_hash(self):
        return self.event_hash

    def to_dict(self, public=True):
        """The public page shows the actor's role only; emails are personal data."""
        data = {"event_type": self.event_type, "timestamp": self.timestamp, "actor_role": self.actor_role,
                "details": self.details, "event_hash": self.event_hash}
        if not public:
            data["actor_email"] = self.actor_email
        return data


@dataclass
class ProductRow:
    id: int
    uuid: str
    name: str
    model: str
    category: str
    lifespan_years: float
    spare_parts_percent: float | None
    owner_id: int | None
    archived: bool
    created_at: str
    materials: list[MaterialRow] = field(default_factory=list)  # active materials only
    history: list[HistoryEventRow] = field(default_factory=list)

    @classmethod
    def from_db(cls, r):
        return cls(r["id"], r["uuid"], r["name"], r["model"], r["category"], r["lifespan_years"],
                   r["spare_parts_percent"], r["owner_id"], bool(r["archived"]), r["created_at"])
