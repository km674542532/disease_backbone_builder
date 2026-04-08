"""Minimal local subset of pydantic used for this repository's MVP tests."""
from __future__ import annotations

from dataclasses import MISSING
import types
from typing import Any, Dict, get_args, get_origin, Literal, Union, get_type_hints


class ValidationError(Exception):
    """Validation error compatible placeholder."""


class FieldInfo:
    def __init__(self, default: Any = MISSING, default_factory: Any = MISSING):
        self.default = default
        self.default_factory = default_factory


def Field(default: Any = MISSING, *, default_factory: Any = MISSING):
    return FieldInfo(default=default, default_factory=default_factory)


class ConfigDict(dict):
    pass


class BaseModel:
    model_config = ConfigDict(extra="ignore")

    def __init__(self, **data: Any):
        values = self._validate_dict(data)
        for k, v in values.items():
            setattr(self, k, v)

    @classmethod
    def model_validate(cls, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValidationError("Input must be dict")
        return cls(**data)

    def model_dump(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for name in self.__annotations__:
            val = getattr(self, name)
            out[name] = _dump_value(val)
        return out

    @classmethod
    def _validate_dict(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        annotations = get_type_hints(cls, include_extras=True)
        values: Dict[str, Any] = {}
        extra_mode = getattr(cls, "model_config", {}).get("extra", "ignore")
        if extra_mode == "forbid":
            for key in data:
                if key not in annotations:
                    raise ValidationError(f"extra field: {key}")
        for name, anno in annotations.items():
            default_info = getattr(cls, name, MISSING)
            has_value = name in data
            if has_value:
                raw = data[name]
            else:
                if isinstance(default_info, FieldInfo):
                    if default_info.default_factory is not MISSING:
                        raw = default_info.default_factory()
                    elif default_info.default is not MISSING:
                        raw = default_info.default
                    else:
                        raise ValidationError(f"missing required field: {name}")
                elif default_info is not MISSING:
                    raw = default_info
                else:
                    raise ValidationError(f"missing required field: {name}")
            values[name] = _validate_type(raw, anno, name)
        return values


def _is_optional(tp: Any) -> bool:
    origin = get_origin(tp)
    args = get_args(tp)
    return origin in (Union, types.UnionType) and type(None) in args


def _validate_type(value: Any, tp: Any, field_name: str) -> Any:
    origin = get_origin(tp)
    args = get_args(tp)

    if _is_optional(tp):
        inner = [a for a in args if a is not type(None)][0]
        if value is None:
            return None
        return _validate_type(value, inner, field_name)

    if origin is Literal:
        if value not in args:
            raise ValidationError(f"invalid literal for {field_name}: {value}")
        return value

    if origin in (list,):
        if not isinstance(value, list):
            raise ValidationError(f"expected list for {field_name}")
        inner = args[0] if args else Any
        return [_validate_type(v, inner, field_name) for v in value]

    if origin in (dict,):
        if not isinstance(value, dict):
            raise ValidationError(f"expected dict for {field_name}")
        k_tp = args[0] if args else Any
        v_tp = args[1] if len(args) > 1 else Any
        return {_validate_type(k, k_tp, field_name): _validate_type(v, v_tp, field_name) for k, v in value.items()}

    if tp is Any:
        return value

    if isinstance(tp, type) and issubclass(tp, BaseModel):
        if isinstance(value, tp):
            return value
        if isinstance(value, dict):
            return tp.model_validate(value)
        raise ValidationError(f"expected object for {field_name}")

    if origin in (Union, types.UnionType):
        for arg in args:
            try:
                return _validate_type(value, arg, field_name)
            except ValidationError:
                continue
        raise ValidationError(f"invalid union for {field_name}")

    if tp in (str, int, float, bool):
        if not isinstance(value, tp):
            raise ValidationError(f"expected {tp.__name__} for {field_name}")
        return value

    return value


def _dump_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump()
    if isinstance(value, list):
        return [_dump_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _dump_value(v) for k, v in value.items()}
    return value
