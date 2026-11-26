#!/usr/bin/env python3
"""Apply the optional global enemy-template API to a clean rivet_hook checkout.

Pinned against neptuwunium/rivet_hook develop as inspected on 2026-11-26.
The patch adds rivet.template_actor(path, uid), which asynchronously loads an
actor asset, creates a resident actor through the same native SpawnActorFromAsset
path already used by rivet.rift, assigns a stable high-bit UID, and marks it as
an inactive template source. It never spawns a combat enemy itself.
"""
from pathlib import Path
import sys

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "rivet_hook")

def replace_once(path, old, new):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != 1:
        raise SystemExit(f"{path}: expected one patch anchor, found {n}: {old[:90]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

def replace_count(path, old, new, expected):
    p = ROOT / path
    s = p.read_text(encoding="utf-8")
    n = s.count(old)
    if n != expected:
        raise SystemExit(f"{path}: expected {expected} patch anchors, found {n}: {old[:90]!r}")
    p.write_text(s.replace(old, new), encoding="utf-8")

replace_once(
    "src/travel.hpp",
    "\t// the hash of a checkpoint the level has, by exact name or as 0x hex text,\n",
    "\t// A resident, inactive template actor made from an actor asset. The uid must\n"
    "\t// be a unique high-bit uid (the same namespace as zone-placed actors).\n"
    "\tenum class TemplateResult { Loading, Loaded, Ready, Failed };\n"
    "\tauto\n"
    "\ttemplate_actor(const char *path, uint64_t uid, bool create, uint32_t *handle, uint32_t *flags,\n"
    "\t\t\t\t   char *message, size_t message_size, const char **reason) -> TemplateResult;\n\n"
    "\t// the hash of a checkpoint the level has, by exact name or as 0x hex text,\n"
)

replace_once(
    "src/travel.cpp",
    "\tstatic PendingRift g_pending;\n",
    "\tstatic PendingRift g_pending;\n"
    "\n"
    "\t// Actor assets stay referenced for the session. The scene actor is a hidden,\n"
    "\t// inactive template source; encounter spawners clone from its actor asset.\n"
    "\tstruct PinnedTemplate {\n"
    "\t\tstd::string path;\n"
    "\t\tAsset *asset = nullptr;\n"
    "\t};\n"
    "\tstatic std::vector<PinnedTemplate> g_templates;\n"
)

replace_once(
    "src/travel.cpp",
    "\tauto\n"
    "\toverlay(const char *region, const bool load, char *message, const size_t message_size, const char **reason) -> bool {\n",
    "\tauto\n"
    "\ttemplate_actor(const char *path, const uint64_t uid, const bool create, uint32_t *handle, uint32_t *flags,\n"
    "\t\t\t\t   char *message, const size_t message_size, const char **reason) -> TemplateResult {\n"
    "\t\tif (message != nullptr && message_size > 0) message[0] = '\\0';\n"
    "\t\tif (handle != nullptr) *handle = 0;\n"
    "\t\tif (flags != nullptr) *flags = 0;\n"
    "\t\tif (path == nullptr || path[0] == '\\0' || strlen(path) >= 0x200) {\n"
    "\t\t\tfail(reason, \"actor asset path is empty or too long\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (uid == 0 || (uid & (1ull << 63)) == 0) {\n"
    "\t\t\tfail(reason, \"template uid must be nonzero and have bit 63 set\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (!game_thread::on_game_thread()) {\n"
    "\t\t\tfail(reason, \"template actors can only be created on the game thread\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (g_SceneManager == nullptr || g_load_actor_asset == nullptr || g_actor_assets == nullptr ||\n"
    "\t\t\t(create && (g_spawn_actor == nullptr || g_set_actor_uid == nullptr))) {\n"
    "\t\t\tfail(reason, \"native actor asset loading or spawning was not found\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\n"
    "\t\tAsset *asset = nullptr;\n"
    "\t\tfor (auto &entry : g_templates) {\n"
    "\t\t\tif (entry.path == path) { asset = entry.asset; break; }\n"
    "\t\t}\n"
    "\t\tif (asset == nullptr) {\n"
    "\t\t\tif (!call_load_asset(path, &asset) || asset == nullptr || !ddl::is_readable(asset, sizeof(Asset))) {\n"
    "\t\t\t\tfail(reason, \"the actor asset could not be requested\"); return TemplateResult::Failed;\n"
    "\t\t\t}\n"
    "\t\t\tg_templates.push_back({ path, asset });\n"
    "\t\t}\n"
    "\t\tif (!ddl::is_readable(asset, sizeof(Asset))) {\n"
    "\t\t\tfail(reason, \"the pinned actor asset pointer is no longer readable\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (asset->status == AssetStatus::Error || asset->status == AssetStatus::Aborted) {\n"
    "\t\t\tfail(reason, \"the actor asset failed to load\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (asset->status != AssetStatus::Loaded) {\n"
    "\t\t\tif (message != nullptr && message_size > 0) _snprintf_s(message, message_size, _TRUNCATE, \"loading %s\", path);\n"
    "\t\t\treturn TemplateResult::Loading;\n"
    "\t\t}\n"
    "\n"
    "\t\t// Reuse our actor after a planet/zone transition if it is still resident.\n"
    "\t\tconst auto existing = scene_query::actor_by_uid(uid);\n"
    "\t\tif (existing != 0) {\n"
    "\t\t\tauto *actor = g_SceneManager->ResolveActor(EngineHandle { .value = existing });\n"
    "\t\t\tif (actor == nullptr || actor->actorAsset == nullptr || !ddl::is_readable(actor->actorAsset, sizeof(Asset)) ||\n"
    "\t\t\t\tactor->actorAsset->assetId != asset->assetId) {\n"
    "\t\t\t\tfail(reason, \"synthetic template uid is already owned by a different actor\"); return TemplateResult::Failed;\n"
    "\t\t\t}\n"
    "\t\t\tactor->flags |= ActorFlag::Template;\n"
    "\t\t\tactor->flags &= ~(ActorFlag::Activated | ActorFlag::StartedActive | ActorFlag::UpdateEnabled | (1u << 7) | (1u << 8));\n"
    "\t\t\tactor->zoneIndex = -1;\n"
    "\t\t\tif (handle != nullptr) *handle = existing;\n"
    "\t\t\tif (flags != nullptr) *flags = actor->flags;\n"
    "\t\t\tif (message != nullptr && message_size > 0) _snprintf_s(message, message_size, _TRUNCATE, \"resident template reused: %s\", path);\n"
    "\t\t\treturn TemplateResult::Ready;\n"
    "\t\t}\n"
    "\n"
    "\t\tif (!create) {\n"
    "\t\t\tif (message != nullptr && message_size > 0) _snprintf_s(message, message_size, _TRUNCATE, \"actor asset loaded; waiting for template creation: %s\", path);\n"
    "\t\t\treturn TemplateResult::Loaded;\n"
    "\t\t}\n\n"
    "\t\t// Create far below the playable world. The template bit and disabled update\n"
    "\t\t// flags prevent this resident source from acting as an extra live enemy.\n"
    "\t\tconst float matrix[4][4] = {\n"
    "\t\t\t{ 1.0f, 0.0f, 0.0f, 0.0f }, { 0.0f, 1.0f, 0.0f, 0.0f },\n"
    "\t\t\t{ 0.0f, 0.0f, 1.0f, 0.0f }, { 0.0f, -100000.0f, 0.0f, 1.0f },\n"
    "\t\t};\n"
    "\t\tActor *actor = nullptr;\n"
    "\t\tif (!call_spawn(asset->assetId, matrix, uid, &actor)) {\n"
    "\t\t\tfail(reason, \"native SpawnActorFromAsset raised an exception for the loaded actor asset\");\n"
    "\t\t\treturn TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (actor == nullptr) {\n"
    "\t\t\tif (message != nullptr && message_size > 0) {\n"
    "\t\t\t\t_snprintf_s(message, message_size, _TRUNCATE, \"native SpawnActorFromAsset returned null (assetId 0x%016llX, status %u): %s\",\n"
    "\t\t\t\t\tstatic_cast<unsigned long long>(asset->assetId), static_cast<unsigned>(asset->status), path);\n"
    "\t\t\t}\n"
    "\t\t\tfail(reason, \"native SpawnActorFromAsset returned a null actor\");\n"
    "\t\t\treturn TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (!ddl::is_writable(actor, sizeof(Actor))) {\n"
    "\t\t\tfail(reason, \"native SpawnActorFromAsset returned an unwritable actor pointer\");\n"
    "\t\t\treturn TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tactor->zoneIndex = -1;\n"
    "\t\tactor->flags |= ActorFlag::Template;\n"
    "\t\tactor->flags &= ~(ActorFlag::Activated | ActorFlag::StartedActive | ActorFlag::UpdateEnabled | (1u << 7) | (1u << 8));\n"
    "\t\tif (actor->object != nullptr && ddl::is_writable(actor->object, sizeof(SceneObject))) {\n"
    "\t\t\tactor->object->transform_matrix[3][0] = 0.0f;\n"
    "\t\t\tactor->object->transform_matrix[3][1] = -100000.0f;\n"
    "\t\t\tactor->object->transform_matrix[3][2] = 0.0f;\n"
    "\t\t}\n"
    "\t\tconst auto created = scene_query::handle_of(actor);\n"
    "\t\tif (created == 0 || scene_query::actor_by_uid(uid) != created || actor->actorAsset == nullptr ||\n"
    "\t\t\t!ddl::is_readable(actor->actorAsset, sizeof(Asset)) || actor->actorAsset->assetId != asset->assetId ||\n"
    "\t\t\t(actor->flags & ActorFlag::Template) == 0) {\n"
    "\t\t\tfail(reason, \"created actor did not pass template/uid read-back checks\"); return TemplateResult::Failed;\n"
    "\t\t}\n"
    "\t\tif (handle != nullptr) *handle = created;\n"
    "\t\tif (flags != nullptr) *flags = actor->flags;\n"
    "\t\tif (message != nullptr && message_size > 0) _snprintf_s(message, message_size, _TRUNCATE, \"resident template created: %s\", path);\n"
    "\t\treturn TemplateResult::Ready;\n"
    "\t}\n"
    "\n"
    "\tauto\n"
    "\toverlay(const char *region, const bool load, char *message, const size_t message_size, const char **reason) -> bool {\n"
)

replace_once(
    "src/scripting.cpp",
    "\tstatic const luaL_Reg g_api[] = {\n",
    "\t// rivet.template_actor(path, uid) -> status, handle, flags, message.\n"
    "\t// Loads and pins an actor asset, then creates a hidden inactive template source.\n"
    "\tstatic auto\n"
    "\tl_template_actor(lua_State *L) -> int {\n"
    "\t\tconst auto *path = luaL_checkstring(L, 1);\n"
    "\t\tconst auto *uid_text = luaL_checkstring(L, 2);\n"
    "\t\tchar *end = nullptr;\n"
    "\t\tconst auto uid = _strtoui64(uid_text, &end, 16);\n"
    "\t\tif (end == uid_text || end == nullptr || *end != '\\0') {\n"
    "\t\t\tlua_pushstring(L, \"failed\"); lua_pushinteger(L, 0); lua_pushinteger(L, 0);\n"
    "\t\t\tlua_pushstring(L, \"uid must be 16-digit hexadecimal text\"); return 4;\n"
    "\t\t}\n"
    "\t\tuint32_t handle = 0, flags = 0;\n"
    "\t\tchar message[0x180] {};\n"
    "\t\tconst char *reason = nullptr;\n"
    "\t\tconst auto create = lua_isnoneornil(L, 3) || lua_toboolean(L, 3) != 0;\n"
    "\t\tconst auto result = travel::template_actor(path, uid, create, &handle, &flags, message, sizeof(message), &reason);\n"
    "\t\tlua_pushstring(L, result == travel::TemplateResult::Ready ? \"ready\" :\n"
    "\t\t\t(result == travel::TemplateResult::Loaded ? \"loaded\" :\n"
    "\t\t\t(result == travel::TemplateResult::Loading ? \"loading\" : \"failed\")));\n"
    "\t\tlua_pushinteger(L, handle);\n"
    "\t\tlua_pushinteger(L, flags);\n"
    "\t\tlua_pushstring(L, message[0] != '\\0' ? message : (reason != nullptr ? reason : \"\"));\n"
    "\t\treturn 4;\n"
    "\t}\n\n"
    "\tstatic const luaL_Reg g_api[] = {\n"
)

replace_once(
    "src/scripting.cpp",
    "\t\t{ \"overlay\", l_overlay },\n",
    "\t\t{ \"overlay\", l_overlay },\n"
    "\t\t{ \"template_actor\", l_template_actor },\n"
)

# A UID collision is never converted into a template actor. Only actors already
# marked as templates by this patch are accepted on subsequent calls. Clear both
# zone- and level-unload bits so the resident sources survive region transitions.
replace_once(
    "src/travel.cpp",
    "\t\t\t\tactor->actorAsset->assetId != asset->assetId) {\n",
    "\t\t\t\tactor->actorAsset->assetId != asset->assetId || (actor->flags & ActorFlag::Template) == 0) {\n",
)


print("Applied global enemy-template API patch.")
