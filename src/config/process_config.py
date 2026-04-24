"""Produkt- und Prozesskonfiguration aus JSON-Dateien."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FieldDef:
    id: str
    display_name: str
    type: str  # "text" | "number" | "choice"
    role: str  # "context" | "measurement" | "auto"
    persistent: bool = False
    spec_target: float | None = None
    spec_min: float | None = None
    spec_max: float | None = None
    options: list[str] | None = None
    optional: bool = False
    default_value: str | None = None
    group_shared: bool = False


@dataclass
class ProcessConfig:
    template_id: str
    display_name: str
    fields: list[FieldDef]
    row_group_size: int | None = None


@dataclass
class ProductConfig:
    product_id: str
    display_name: str
    processes: list[ProcessConfig]
    output_dir: str | None = None


@dataclass
class ShiftDef:
    name: str
    start_hour: int
    end_hour: int


@dataclass
class AppConfig:
    products: list[ProductConfig] = field(default_factory=list)
    output_dir: str = "output"
    shifts: list[ShiftDef] = field(default_factory=list)
    qr_prefix: str = ""


def _parse_field(data: dict) -> FieldDef:
    return FieldDef(
        id=data["id"],
        display_name=data["display_name"],
        type=data.get("type", "text"),
        role=data.get("role", "measurement"),
        persistent=data.get("persistent", False),
        spec_target=data.get("spec_target"),
        spec_min=data.get("spec_min"),
        spec_max=data.get("spec_max"),
        options=data.get("options"),
        optional=data.get("optional", False),
        default_value=data.get("default_value"),
        group_shared=data.get("group_shared", False),
    )


def _parse_process(data: dict) -> ProcessConfig:
    return ProcessConfig(
        template_id=data["template_id"],
        display_name=data["display_name"],
        fields=[_parse_field(f) for f in data["fields"]],
        row_group_size=data.get("row_group_size"),
    )


def load_product_config(path: Path) -> ProductConfig:
    """Lädt eine Produkt-Konfiguration aus einer JSON-Datei."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return ProductConfig(
        product_id=data["product_id"],
        display_name=data["display_name"],
        processes=[_parse_process(p) for p in data["processes"]],
        output_dir=data.get("output_dir"),
    )


def load_app_config(config_path: Path, products_dir: Path) -> AppConfig:
    """Lädt globale Settings und alle Produktdateien."""
    if config_path.exists():
        global_data = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        global_data = {}

    shifts = [
        ShiftDef(
            name=s["name"],
            start_hour=s["start_hour"],
            end_hour=s["end_hour"],
        )
        for s in global_data.get("shifts", [])
    ]

    products: list[ProductConfig] = []
    if products_dir.exists():
        for p in sorted(products_dir.glob("*.json")):
            products.append(load_product_config(p))

    return AppConfig(
        products=products,
        output_dir=global_data.get("output_dir", "output"),
        shifts=shifts,
        qr_prefix=global_data.get("qr_prefix", ""),
    )


def get_context_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "context"]


def get_persistent_context_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "context" and f.persistent]


def get_per_measurement_context_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "context" and not f.persistent]


def get_measurement_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "measurement"]


def get_group_shared_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "measurement" and f.group_shared]


def get_per_nutzen_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "measurement" and not f.group_shared]


def get_auto_fields(process: ProcessConfig) -> list[FieldDef]:
    return [f for f in process.fields if f.role == "auto"]


def get_all_headers(process: ProcessConfig) -> list[str]:
    return [f.display_name for f in process.fields]


def get_field_by_id(process: ProcessConfig, field_id: str) -> FieldDef | None:
    for f in process.fields:
        if f.id == field_id:
            return f
    return None


def determine_shift(hour: int, shifts: list[ShiftDef]) -> str:
    """Bestimmt die Schicht für die aktuelle Stunde.

    Berücksichtigt Schichten über Mitternacht (z.B. 22-06).
    """
    for shift in shifts:
        if shift.start_hour < shift.end_hour:
            if shift.start_hour <= hour < shift.end_hour:
                return shift.name
        else:
            if hour >= shift.start_hour or hour < shift.end_hour:
                return shift.name

    return "1"
