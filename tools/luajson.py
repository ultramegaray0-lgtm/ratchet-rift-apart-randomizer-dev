"""Lua table <-> Python helpers for offline tools (lupa, Lua 5.4)."""
from lupa import lua54


def py(o):
    if lua54.lua_type(o) == "table":
        keys = list(o.keys())
        if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
            return [py(o[k]) for k in sorted(keys)]
        return {str(k): py(v) for k, v in o.items()}
    return o
