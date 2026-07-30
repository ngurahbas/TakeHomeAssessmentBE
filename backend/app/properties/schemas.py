from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class PropertyType(StrEnum):
    APARTMENT = "APARTMENT"
    HOUSE = "HOUSE"
    VILLA = "VILLA"
    STUDIO = "STUDIO"
    OFFICE = "OFFICE"
    LAND = "LAND"


class ListingType(StrEnum):
    SALE = "SALE"
    RENT = "RENT"


class PropertyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    SOLD = "SOLD"
    RENTED = "RENTED"


class PropertyImageIn(BaseModel):
    url: HttpUrl
    sort_order: int = Field(default=0, ge=0)
    alt: str | None = Field(default=None, max_length=200)


_NOT_NULL_UPDATE_FIELDS: tuple[str, ...] = (
    "title",
    "description",
    "property_type",
    "listing_type",
    "price_amount",
    "price_currency",
    "address_line",
    "city",
    "country_code",
    "status",
)


class PropertyImageOut(PropertyImageIn):
    pass


class PropertyCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=10_000)
    property_type: PropertyType
    listing_type: ListingType
    price_amount: float = Field(..., ge=0)
    price_currency: str = Field(..., min_length=3, max_length=3)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: int | None = Field(default=None, ge=0, le=50)
    area_sqm: float | None = Field(default=None, ge=0, le=100_000)
    address_line: str = Field(..., min_length=1, max_length=255)
    city: str = Field(..., min_length=1, max_length=128)
    district: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    country_code: str = Field(..., min_length=2, max_length=2)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: PropertyStatus = Field(default=PropertyStatus.AVAILABLE)
    amenities: list[str] = Field(default_factory=list)
    images: list[PropertyImageIn] = Field(default_factory=list)

    @field_validator("price_currency", "country_code")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("title", "city", "address_line")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @field_validator("amenities")
    @classmethod
    def _dedup_lower(cls, v: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out


class PropertyUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10_000)
    property_type: PropertyType | None = None
    listing_type: ListingType | None = None
    price_amount: float | None = Field(default=None, ge=0)
    price_currency: str | None = Field(default=None, min_length=3, max_length=3)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    bathrooms: int | None = Field(default=None, ge=0, le=50)
    area_sqm: float | None = Field(default=None, ge=0, le=100_000)
    address_line: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=128)
    district: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=32)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    status: PropertyStatus | None = None
    amenities: list[str] | None = None
    images: list[PropertyImageIn] | None = None

    @field_validator("price_currency", "country_code")
    @classmethod
    def _upper(cls, v: str | None) -> str | None:
        return v.upper() if v is not None else None

    @field_validator("title", "city", "address_line")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None

    @field_validator("amenities")
    @classmethod
    def _dedup_lower(
        cls, v: list[str] | None
    ) -> list[str] | None:
        if v is None:
            return None
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            key = item.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    @model_validator(mode="after")
    def _reject_null_for_required(self) -> PropertyUpdate:
        for name in _NOT_NULL_UPDATE_FIELDS:
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class PropertyOut(BaseModel):
    id: int
    title: str
    description: str
    property_type: PropertyType
    listing_type: ListingType
    price_amount: float
    price_currency: str
    bedrooms: int | None
    bathrooms: int | None
    area_sqm: float | None
    address_line: str
    city: str
    district: str | None
    postal_code: str | None
    country_code: str
    latitude: float | None
    longitude: float | None
    status: PropertyStatus
    amenities: list[str]
    images: list[PropertyImageOut]
    created_at: str
    updated_at: str
    created_by: int | None
    updated_by: int | None


class PropertyListItem(BaseModel):
    id: int
    title: str
    property_type: PropertyType
    listing_type: ListingType
    price_amount: float
    price_currency: str
    city: str
    country_code: str
    status: PropertyStatus
    bedrooms: int | None
    bathrooms: int | None
    area_sqm: float | None
    images: list[PropertyImageOut]
    created_at: str


class PropertyList(BaseModel):
    items: list[PropertyListItem]
    total: int
    limit: int
    offset: int
