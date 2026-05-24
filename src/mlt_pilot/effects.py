"""Catalog of MLT filters, effects, and transitions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EffectParameter:
    """Descriptor for a single effect parameter."""
    name: str                      # MLT property name
    display_name: str              # Human-readable name
    param_type: str                # "float", "int", "string", "color", "keyframe"
    default: str | int | float     # Default value
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    description: str = ""


@dataclass
class EffectDefinition:
    """Definition of an MLT filter or transition service."""
    service: str
    display_name: str
    category: str                  # "color", "audio", "transform", "transition", "blur"
    description: str = ""
    parameters: list[EffectParameter] = field(default_factory=list)


FILTERS: dict[str, EffectDefinition] = {}
TRANSITIONS: dict[str, EffectDefinition] = {}


def register_filter(definition: EffectDefinition) -> None:
    FILTERS[definition.service] = definition


def register_transition(definition: EffectDefinition) -> None:
    TRANSITIONS[definition.service] = definition


def get_filter(service: str) -> EffectDefinition:
    if service not in FILTERS:
        available = ", ".join(sorted(FILTERS.keys()))
        raise KeyError(f"Unknown filter: {service!r}. Available: {available}")
    return FILTERS[service]


def get_transition(service: str) -> EffectDefinition:
    if service not in TRANSITIONS:
        available = ", ".join(sorted(TRANSITIONS.keys()))
        raise KeyError(f"Unknown transition: {service!r}. Available: {available}")
    return TRANSITIONS[service]


def list_filters(category: Optional[str] = None) -> list[EffectDefinition]:
    if category:
        return [f for f in FILTERS.values() if f.category == category]
    return list(FILTERS.values())


def list_transitions() -> list[EffectDefinition]:
    return list(TRANSITIONS.values())


def resolve_transition_type(transition_name: str) -> dict[str, str]:
    """
    Map a high-level transition name to MLT service + default properties.
    
    Returns dict with: "service" (str), "properties" (dict).
    Raises ValueError for unknown names.
    """
    mappings = {
        "crossfade": {
            "service": "composite",
            "properties": {
                "composite.progress": "0=0;100=100",
                "composite": "0%,0%:100%x100%:100",
            },
        },
        "dissolve": {
            "service": "luma",
            "properties": {
                "luma softenness": "0",
            },
        },
        "wipe": {
            "service": "luma",
            "properties": {
                "resource": "%luma%/all_wipes.pgm",
                "luma softenness": "0",
            },
        },
        "overlay": {
            "service": "composite",
            "properties": {
                "composite": "0%,0%:100%x100%:100",
                "composite.operator": "over",
            },
        },
        "mix": {
            "service": "mix",
            "properties": {
                "start": "0",
                "end": "100",
            },
        },
    }
    
    if transition_name not in mappings:
        available = ", ".join(sorted(mappings.keys()))
        raise ValueError(f"Unknown transition type: {transition_name!r}. Available: {available}")
    
    return mappings[transition_name]


def build_filter_properties(service: str, **kwargs) -> dict[str, str]:
    """
    Build a properties dict for an MLT filter.
    Validates parameter names against catalog. Unknown params are passed through with warning.
    All values converted to strings.
    """
    properties = {}
    
    # Try to validate against known catalog
    if service in FILTERS:
        known_params = {p.name for p in FILTERS[service].parameters}
        for key, value in kwargs.items():
            if key not in known_params:
                logger.warning(f"Unknown parameter {key!r} for filter {service!r}")
            properties[key] = str(value)
    else:
        # No catalog entry, pass everything through
        for key, value in kwargs.items():
            properties[key] = str(value)
    
    return properties


def _register_defaults() -> None:
    """Register all built-in filter and transition definitions."""
    
    # ── Audio Filters ─────────────────────────────────────────────────────
    register_filter(EffectDefinition(
        service="volume", display_name="Volume", category="audio",
        description="Audio volume control",
        parameters=[
            EffectParameter("gain", "Gain", "float", 1.0, 0, 10),
            EffectParameter("normalise", "Normalize", "int", 0, 0, 1),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="loudness", display_name="Loudness", category="audio",
        description="EBU R128 loudness normalization",
        parameters=[
            EffectParameter("loudness", "Target LUFS", "float", -23.0),
        ],
    ))
    
    # ── Color Filters ──────────────────────────────────────────────────────
    register_filter(EffectDefinition(
        service="brightness", display_name="Brightness", category="color",
        description="Brightness and contrast adjustment",
        parameters=[
            EffectParameter("brightness", "Brightness", "float", 0, -1, 1),
            EffectParameter("contrast", "Contrast", "float", 1, 0, 10),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="gamma", display_name="Gamma", category="color",
        description="Gamma correction",
        parameters=[
            EffectParameter("gamma", "Gamma", "float", 1.0, 0.1, 10),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="saturate", display_name="Saturation", category="color",
        description="Color saturation control",
        parameters=[
            EffectParameter("level", "Saturation Level", "float", 1.0, 0, 10),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="hue", display_name="Hue", category="color",
        description="Hue rotation",
        parameters=[
            EffectParameter("level", "Hue Angle", "float", 0, 0, 360),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="greyscale", display_name="Greyscale", category="color",
        description="Convert to greyscale",
    ))
    
    # ── Transform Filters ─────────────────────────────────────────────────
    register_filter(EffectDefinition(
        service="affine", display_name="Affine Transform", category="transform",
        description="Position, rotation, scale",
        parameters=[
            EffectParameter("transition.rotate", "Rotation", "float", 0),
            EffectParameter("transition.scale_x", "Scale X", "float", 1.0),
            EffectParameter("transition.scale_y", "Scale Y", "float", 1.0),
            EffectParameter("transition.x", "Position X", "float", 0),
            EffectParameter("transition.y", "Position Y", "float", 0),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="resize", display_name="Resize", category="transform",
        description="Scale and fit",
        parameters=[
            EffectParameter("scale", "Scale", "float", 1.0),
            EffectParameter("mode", "Mode", "string", "fit"),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="mirror", display_name="Mirror", category="transform",
        description="Horizontal/vertical flip",
        parameters=[
            EffectParameter("mirror", "Direction", "string", "horizontal"),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="opacity", display_name="Opacity", category="transform",
        description="Opacity control",
        parameters=[
            EffectParameter("opacity", "Opacity", "float", 1.0, 0, 1),
        ],
    ))
    
    # ── Blur Filters ───────────────────────────────────────────────────────
    register_filter(EffectDefinition(
        service="boxblur", display_name="Box Blur", category="blur",
        description="Box blur effect",
        parameters=[
            EffectParameter("start", "Radius", "float", 0, 0, 20),
            EffectParameter("type", "Type", "string", "box"),
        ],
    ))
    
    register_filter(EffectDefinition(
        service="glow", display_name="Glow", category="blur",
        description="Glow effect",
        parameters=[
            EffectParameter("blur_start", "Blur", "float", 0),
            EffectParameter("brightness_start", "Brightness", "float", 1.0),
        ],
    ))
    
    # ── Misc Filters ──────────────────────────────────────────────────────
    register_filter(EffectDefinition(
        service="freeze", display_name="Freeze Frame", category="transform",
        description="Freeze at a specific frame",
        parameters=[
            EffectParameter("frame", "Frame", "int", 0),
            EffectParameter("freeze_after", "Freeze After", "int", 0),
        ],
    ))
    
    # ── Transitions ───────────────────────────────────────────────────────
    register_transition(EffectDefinition(
        service="composite", display_name="Composite", category="transition",
        description="Composite/overlay two tracks",
        parameters=[
            EffectParameter("a_track", "Track A", "int", 0),
            EffectParameter("b_track", "Track B", "int", 1),
            EffectParameter("composite", "Geometry", "string", "0%,0%:100%x100%:100"),
        ],
    ))
    
    register_transition(EffectDefinition(
        service="mix", display_name="Mix", category="transition",
        description="Audio/video crossfade",
        parameters=[
            EffectParameter("a_track", "Track A", "int", 0),
            EffectParameter("b_track", "Track B", "int", 1),
            EffectParameter("start", "Start Mix", "float", 0),
            EffectParameter("end", "End Mix", "float", 100),
        ],
    ))
    
    register_transition(EffectDefinition(
        service="luma", display_name="Luma Wipe", category="transition",
        description="Luma-based wipe/dissolve",
        parameters=[
            EffectParameter("resource", "Luma Resource", "string", ""),
            EffectParameter("softness", "Softness", "float", 0),
            EffectParameter("progress", "Progress", "float", 0),
        ],
    ))


_register_defaults()
