from pydantic import BaseModel, ConfigDict, Field


class MaterialIn(BaseModel):
    material: str | None = Field(None, examples=["Aluminium"])
    percent: float | None = Field(None, description="Share of the product's mass, 0-100.", examples=[60])
    recycled: float = Field(0, ge=0, le=100, description="Recycled share of this material, 0-100.")
    recyclable: bool = True
    hazard: bool = False


class ProductIn(BaseModel):
    name: str | None = Field(None, examples=["EcoBook 14"])
    model: str | None = Field("", examples=["EB-14"])
    category: str | None = Field(None, examples=["Laptop"])
    lifespan_years: float | None = Field(None, examples=[6])
    spare_parts_percent: float | None = Field(None, description="Optional, used for the score.", examples=[80])
    materials: list[MaterialIn] | None = None


class ProductUpdate(BaseModel):
    """Only the fields that are sent are changed. The UUID can never be changed."""
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    model: str | None = None
    category: str | None = None
    lifespan_years: float | None = None
    spare_parts_percent: float | None = None
    materials: list[MaterialIn] | None = None


class MaterialOut(BaseModel):
    material: str
    percent: float
    recycled: float
    recyclable: bool
    hazard: bool


class HistoryEventOut(BaseModel):
    event_type: str
    timestamp: str
    actor_role: str
    details: str
    event_hash: str


class SubScoreOut(BaseModel):
    name: str
    label: str
    value: float | None
    weight: float
    points: float


class ScoreOut(BaseModel):
    total: float
    grade: str
    incomplete: bool
    missing: list[str]
    sub_scores: list[SubScoreOut]


class HistoryCheck(BaseModel):
    valid: bool
    first_broken_event: int | None


class PassportOut(BaseModel):
    uuid: str
    name: str
    model: str
    category: str
    lifespan_years: float
    spare_parts_percent: float | None
    materials: list[MaterialOut]
    public_url: str
    qr_code_url: str
    circularity_score: ScoreOut | None
    history: list[HistoryEventOut]
    history_check: HistoryCheck
    archived: bool
    created_at: str | None


class ProductSummary(BaseModel):
    uuid: str
    name: str
    model: str
    category: str
    archived: bool
    public_url: str


class SearchResult(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[ProductSummary]


class EventIn(BaseModel):
    event_type: str = Field(..., examples=["repaired"],
                            description="manufactured, sold, used, repaired, refurbished or recycled")
    details: str = Field("", max_length=1000, examples=["Battery replaced"])


class Credentials(BaseModel):
    email: str = Field(..., examples=["anna@example.com"])
    password: str = Field(..., examples=["s3cretPass!"])


class NewUser(Credentials):
    role: str = Field("consumer", examples=["manufacturer"])


class RoleChange(BaseModel):
    role: str = Field(..., examples=["recycler"])


class UserOut(BaseModel):
    email: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class ErrorOut(BaseModel):
    detail: str
    missing_fields: list[str] | None = None
