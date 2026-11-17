/* Host unit test for rando_give_core.h (the portable part of rando_give.dll).
 * Build: cc -O1 -Wall -Wextra -Werror -I<mod>/rando_give_source test_rando_give_core.c */
#include <stdio.h>
#include <string.h>
#include "rando_give_core.h"

static int failures;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); ++failures; } } while (0)

static u8 mailbox[0x1000];
static u64 sent_item;
static u32 sent_count, sent_targets, sent_calls, group_asked, group_size = 1;
static u32 actor_store[4] = { 77, 0, 0, 0 };

static void *fake_get_players(void *players, rg_actor_list *out, u32 index) {
	(void)players;
	group_asked = index;
	out->ptr = group_size ? actor_store : 0;
	out->count = group_size;
	return out;
}
static void fake_send(u32 mode, u64 message, void *targets, u32 count, void *payload, u32 size) {
	(void)mode; (void)message; (void)targets;
	CHECK(size == 0xC);
	sent_item = *(u64 *)payload;
	sent_count = *(u32 *)((u8 *)payload + 8);
	sent_targets = count;
	sent_calls++;
}
static u32 direct_give(rg_state *s, u64 item, u32 count, u32 hero, u32 mode, u32 *t, u32 *p) {
	return rg_give(s, item, count, hero, mode, t, p);
}

/* ---- v3: a fake mission manager that behaves like the game's code (states per index) ---- */
static u32 ms_hashes[3];
static u32 ms_states[3];
static u8 ms_is_ready = 1;
static u32 ms_make_calls, ms_start_calls, ms_set_calls, ms_last_flag;
static const char *ms_last_name;
static int ms_index_of(u32 h) {
	for (int i = 0; i < 3; ++i) if (ms_hashes[i] == h) return i;
	return -1;
}
static u8 f_ready(void *mgr) { (void)mgr; return ms_is_ready; }
static u32 f_state_by_name(void *mgr, const char *name, u8 flag) {
	(void)mgr; (void)flag;
	int i = ms_index_of(rg_hash(name));
	return i < 0 ? 0 : ms_states[i];
}
static void f_make_a(void *mgr, const char *name, u8 flag) {
	(void)mgr; (void)flag;
	int i = ms_index_of(rg_hash(name));
	if (i >= 0 && ms_states[i] == 0) ms_states[i] = 1;
	ms_make_calls++;
	ms_last_name = name;
}
static void f_make_b(void *mgr, const char *name) { (void)mgr; (void)name; ms_make_calls++; }
static int *f_find(void *mgr, int *out, u32 h) { (void)mgr; *out = ms_index_of(h); return out; }
static u32 f_state_by_index(void *mgr, int i, u8 flag) { (void)mgr; (void)flag; return ms_states[i]; }
static void f_set_state(void *mgr, int i, u32 st) { (void)mgr; ms_states[i] = st; ms_set_calls++; }
static int f_start(void *mgr, const char *name, u8 flag) {
	(void)mgr;
	int i = ms_index_of(rg_hash(name));
	if (i >= 0) ms_states[i] = 3;
	ms_start_calls++;
	ms_last_flag = flag;
	return 7;
}
static u64 fake_vtable[0x40];
static void *fake_mgr_obj[1] = { fake_vtable };
static void *fake_mgr_global;
static u8 fake_alt_flag;
static u32 direct_mission(rg_state *s, u32 kind, const char *name, u32 flag, u32 *b, u32 *a, u32 *r, u32 *x, u64 *o, u32 *sys) {
	return rg_mission(s, kind, name, flag, b, a, r, x, o, sys);
}

/* ---- v4: system 2, missions as components with vtables ---- */
static u32 m2_states[3];
static u32 m2_hashes[3];
static u8 m2_can = 1;
static u32 m2_start_calls, m2_complete_calls, m2_replay_calls, m2_replay_flag;
typedef struct { u64 *vt; int i; } fake_obj;
static fake_obj m2_objs[3];
static u64 m2_vt[0x40];
static void *f2_lookup(void *mgr, rg_ms2_handle *out, u32 h) {
	(void)mgr;
	out->handle = 0; out->component = 0; out->hash = 0;
	for (int i = 0; i < 3; ++i) if (m2_hashes[i] == h) { out->handle = 0x100 + i; out->component = 0xC0 + i; out->hash = h; }
	return out;
}
static u32 f2_state(void *mgr, rg_ms2_handle *h) { (void)mgr; return h->handle ? m2_states[h->handle - 0x100] : 0; }
static void *f2_resolve(rg_ms2_handle *h) { return h->handle ? (void *)&m2_objs[h->handle - 0x100] : 0; }
static void *f2_component(void *ent, u64 c) { (void)c; return ent; }
static u8 f2_can(void *o) { (void)o; return m2_can; }
static void f2_start(void *o) { m2_states[((fake_obj *)o)->i] = 2; m2_start_calls++; }
static void f2_complete(void *o) { m2_states[((fake_obj *)o)->i] = 4; m2_complete_calls++; }
static u8 f2_replay(void *o, u8 flag, u8 one) { (void)o; m2_replay_flag = flag; m2_replay_calls += one; return 1; }

/* ---- v6: mission state records, the level mask, planetary travel ---- */
typedef struct { u8 pad[0x30]; u32 state; u32 tail; } fake_record;
typedef struct { u8 pad[0x28]; fake_record *rec; } fake_entry;
typedef struct { u64 *vt; u8 **p1; int i; } fake_obj6;
static fake_record r6_records[3];
static fake_entry r6_entries[3];
static u8 r6_p2[3][16];
static u8 *r6_p1[3];
static fake_obj6 r6_objs[3];
static u64 r6_vt[0x40];
static u8 *r6_table_expected;
static u32 r6_table_calls, r6_entry_calls, r6_id_calls;
static int r6_break_entry;
static u32 f6_node_id(void *o) { r6_id_calls++; return 0x700 + (u32)((fake_obj6 *)o)->i; }
static void *f6_table(void *table, u64 key) {
	r6_table_calls++;
	if ((u8 *)table != r6_table_expected) return 0;
	return key >= 0xABC0 && key < 0xABC3 ? (void *)&r6_entries[key - 0xABC0] : 0;
}
static void *f6_entry(void *t, u32 id) {
	r6_entry_calls++;
	if (r6_break_entry) return 0;
	fake_entry *e = (fake_entry *)t;
	return (id == 0x700 + (u32)(e - r6_entries)) ? (void *)e : 0;
}
static void *f6_resolve(rg_ms2_handle *h) { return h->handle ? (void *)&r6_objs[h->handle - 0x100] : 0; }
static u32 f6_state(void *mgr, rg_ms2_handle *h) { (void)mgr; return h->handle ? r6_records[h->handle - 0x100].state : 0; }
static u8 l6_levels[0x40];
static u8 l6_travel;
static u32 l6_set_calls;
static void f6_level_set(void *levels, u32 level, u8 on) {
	u32 *m = (u32 *)((u8 *)levels + 0x30);
	l6_set_calls++;
	if (on) *m |= 1u << level; else *m &= ~(1u << level);
}
static u32 direct_level(rg_state *s, u32 kind, u32 flag, u32 level, u32 *b, u32 *a, u32 *r, u32 *x) {
	return rg_level(s, kind, flag, level, b, a, r, x);
}
/* ---- v5: armor, a fake hero with a VanityInventoryManager ---- */
typedef struct { u8 raw[0x100]; } fake_actor;
static fake_actor v_actor;
static u32 v_hero_handle_seen, v_list_used, v_give_calls, v_owned_mask;
static u64 v_last_bundle;
static u8 v_last_flag = 0xEE;
static const void *v_type_seen;
static u8 *v_base;
static int v_no_actor, v_no_mgr;
static u8 v_mgr_obj[16];
static void *fv_resolve(const u32 *h) { v_hero_handle_seen = *h; return v_no_actor ? 0 : (void *)&v_actor; }
static void *fv_find_a(void *list, const void *type) {
	v_list_used = (u32)((u8 *)list - v_actor.raw); v_type_seen = type; return v_no_mgr ? 0 : (void *)v_mgr_obj;
}
static void *fv_find_b(void *list, const void *type) {
	v_list_used = (u32)((u8 *)list - v_actor.raw); v_type_seen = type; return v_no_mgr ? 0 : (void *)v_mgr_obj;
}
static u8 fv_give(void *mgr, u64 bundle, u8 flag) {
	CHECK(mgr == (void *)v_mgr_obj);
	v_give_calls++; v_last_bundle = bundle; v_last_flag = flag;
	u32 bit = 1u << (bundle & 31);
	if (v_owned_mask & bit) return 0;
	v_owned_mask |= bit;
	return 1;
}
static u32 direct_vanity(rg_state *s, u64 bundle, u32 *ret) { return rg_vanity(s, bundle, ret); }
static u32 direct_lookup(rg_state *s, u64 id, u64 *object) { return rg_config_lookup(s, id, object); }
/* v5: the output plug function, faked */
static u32 fire_calls, fire_plug;
static void *fire_ctx;
static u8 fv_fire(void *ctx, u32 plug) { fire_calls++; fire_ctx = ctx; fire_plug = plug; return 1; }
static u32 vanity_req(u32 req, u64 bundle) {
	RG_U32(mailbox, MB_KIND) = RG_KIND_VANITY_GIVE;
	RG_U64(mailbox, MB_ITEM) = bundle;
	RG_U32(mailbox, MB_REQ) = req;
	return req;
}

static void set_slot(u32 slot, const char *text) {
	memset(mailbox + MB_NAMES + slot * RG_NAME_SIZE, 0, RG_NAME_SIZE);
	memcpy(mailbox + MB_NAMES + slot * RG_NAME_SIZE, text, strlen(text));
}
static u32 mission_req(u32 req, u32 kind, u32 slot, u32 flag) {
	RG_U32(mailbox, MB_KIND) = kind;
	RG_U32(mailbox, MB_SLOT) = slot;
	RG_U32(mailbox, MB_FLAG) = flag;
	RG_U32(mailbox, MB_REQ) = req;
	return req;
}

int main(void) {
	static u8 fake_exe[0x7000000];
	u64 msg = 0x1234;
	rg_state s;
	memset(&s, 0, sizeof s);
	s.mailbox = mailbox;
	s.get_players = fake_get_players;
	s.send = fake_send;
	s.message = &msg;

	{ /* rg_resolve points at the RVAs of the image */
		rg_state r;
		memset(&r, 0, sizeof r);
		r.base = fake_exe;
		rg_resolve(&r);
		CHECK((u8 *)r.send == fake_exe + RVA_SEND_MESSAGE && (u8 *)r.message == fake_exe + RVA_ADD_TO_INVENTORY_MSG);
	}
	/* exe verification: a blank image is refused, the expected bytes are accepted */
	CHECK(!rg_verify(fake_exe));
	memcpy(fake_exe + RVA_ADD_TO_INVENTORY_HANDLER, RG_EXPECTED_HANDLER, sizeof RG_EXPECTED_HANDLER);
	memcpy(fake_exe + RVA_SIGNAL_PUMP, RG_EXPECTED_PUMP, sizeof RG_EXPECTED_PUMP);
	memcpy(fake_exe + RVA_GET_PLAYER_ACTORS, RG_EXPECTED_GET_PLAYERS, sizeof RG_EXPECTED_GET_PLAYERS);
	memcpy(fake_exe + RVA_SEND_MESSAGE, RG_EXPECTED_SEND, sizeof RG_EXPECTED_SEND);
	CHECK(rg_verify(fake_exe));
	fake_exe[RVA_ADD_TO_INVENTORY_HANDLER + 0x50] ^= 1;
	CHECK(!rg_verify(fake_exe));

	/* v6: each 8.0 path is checked on its own; the state walk also needs the v4 mission path */
	{
		rg_state r;
		memset(&r, 0, sizeof r);
		r.base = fake_exe;
		CHECK(rg_verify_v6(&r) == 0 && !r.state_ok && !r.levels_ok && !r.travel_ok);
		memcpy(fake_exe + RVA_MS2_STATE, RG_EXPECTED_MS2_STATE_WALK, sizeof RG_EXPECTED_MS2_STATE_WALK);
		memcpy(fake_exe + RVA_UNLOCK_LEVEL_HANDLER, RG_EXPECTED_UNLOCK_LEVEL_HANDLER, sizeof RG_EXPECTED_UNLOCK_LEVEL_HANDLER);
		memcpy(fake_exe + RVA_LEVEL_SET_BIT, RG_EXPECTED_LEVEL_SET, sizeof RG_EXPECTED_LEVEL_SET);
		memcpy(fake_exe + RVA_IS_LEVEL_UNLOCKED, RG_EXPECTED_IS_LEVEL_UNLOCKED, sizeof RG_EXPECTED_IS_LEVEL_UNLOCKED);
		memcpy(fake_exe + RVA_PLANETARY_TRAVEL_HANDLER, RG_EXPECTED_PLANETARY_TRAVEL_HANDLER, sizeof RG_EXPECTED_PLANETARY_TRAVEL_HANDLER);
		CHECK(rg_verify_v6(&r) == (RG_V6_LEVELS | RG_V6_TRAVEL) && !r.state_ok);  /* missions_ok is 0 */
		CHECK((u8 *)r.levels == fake_exe + RVA_LEVELS_GLOBAL && (u8 *)r.level_set == fake_exe + RVA_LEVEL_SET_BIT);
		CHECK((u8 *)r.travel_byte == fake_exe + RVA_PLANETARY_TRAVEL_BYTE);
		r.missions_ok = 1;
		CHECK(rg_verify_v6(&r) == (RG_V6_STATE | RG_V6_LEVELS | RG_V6_TRAVEL) && r.state_ok);
		CHECK((u8 *)r.ms2_table_find == fake_exe + RVA_MS2_TABLE_FIND && (u8 *)r.ms2_entry_find == fake_exe + RVA_MS2_ENTRY_FIND);
		memset(&r, 0, sizeof r); r.base = fake_exe; r.missions_ok = 1;
		fake_exe[RVA_UNLOCK_LEVEL_HANDLER + 0x90] ^= 1;   /* inside the lea that names the global */
		fake_exe[RVA_PLANETARY_TRAVEL_HANDLER + 0x40] ^= 1;
		fake_exe[RVA_MS2_STATE + 0x8E] ^= 1;               /* the +0x30 read */
		CHECK(rg_verify_v6(&r) == 0 && !r.levels_ok && !r.travel_ok && !r.state_ok);
	}

	rg_mailbox_init(mailbox, fake_exe);
	CHECK(RG_U64(mailbox, MB_MAGIC) == RG_MAGIC);
	CHECK(memcmp(mailbox, "RANDGIV1", 8) == 0);
	CHECK(RG_U32(mailbox, MB_VERSION) == 7);

	/* not ready: nothing happens */
	RG_U32(mailbox, MB_REQ) = 1;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(sent_calls == 0 && RG_U32(mailbox, MB_DONE) == 0 && RG_U32(mailbox, MB_PUMPS) == 1);

	/* hero target */
	RG_U32(mailbox, MB_STATUS) = RG_STATUS_READY;
	RG_U64(mailbox, MB_ITEM) = 0xBA124FFA5A2B85CEULL;
	RG_U32(mailbox, MB_COUNT) = 1;
	RG_U32(mailbox, MB_HERO) = 1234;
	RG_U32(mailbox, MB_MODE) = 0;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(sent_calls == 1 && sent_item == 0xBA124FFA5A2B85CEULL && sent_count == 1 && sent_targets == 1);
	CHECK(RG_U32(mailbox, MB_DONE) == 1 && RG_U32(mailbox, MB_RESULT) == RG_RESULT_SENT && RG_U32(mailbox, MB_PATH) == 1);
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level); /* same request is not handled twice */
	CHECK(sent_calls == 1);

	/* group k-1 */
	RG_U32(mailbox, MB_MODE) = 2;
	RG_U32(mailbox, MB_REQ) = 2;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(sent_calls == 2 && group_asked == 1 && RG_U32(mailbox, MB_PATH) == 3);

	/* empty group, no hero, bad requests */
	group_size = 0;
	RG_U32(mailbox, MB_REQ) = 3;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(sent_calls == 2 && RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_TARGET);
	RG_U32(mailbox, MB_MODE) = 0;
	RG_U32(mailbox, MB_HERO) = 0;
	RG_U32(mailbox, MB_REQ) = 4;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_TARGET);
	RG_U32(mailbox, MB_HERO) = 5;
	RG_U32(mailbox, MB_COUNT) = 0;
	RG_U32(mailbox, MB_REQ) = 5;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST);
	RG_U32(mailbox, MB_COUNT) = 1;
	RG_U32(mailbox, MB_MODE) = 65;
	RG_U32(mailbox, MB_REQ) = 6;
	rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
	CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && sent_calls == 2);

	/* ---- v3 mission requests ---- */
	{
		/* the engine hash: values seen in the game (rivet.hash in the research run) */
		CHECK(rg_hash("MIS_INTRO") == 1000115474u);
		CHECK(rg_hash("MIS_RYNO_PLANS") == 921841157u);
		CHECK(rg_hash("MIS_HAX_DEFAULT") == 1715520893u);

		/* verification: blank image refused, expected bytes accepted, one changed byte refused */
		CHECK(!rg_verify_missions(fake_exe));
		memcpy(fake_exe + RVA_MAKE_HANDLER, RG_EXPECTED_MAKE_HANDLER, sizeof RG_EXPECTED_MAKE_HANDLER);
		memcpy(fake_exe + RVA_START_HANDLER, RG_EXPECTED_START_HANDLER, sizeof RG_EXPECTED_START_HANDLER);
		memcpy(fake_exe + RVA_COMPLETE_HANDLER, RG_EXPECTED_COMPLETE_HANDLER, sizeof RG_EXPECTED_COMPLETE_HANDLER);
		memcpy(fake_exe + RVA_MS_READY, RG_EXPECTED_MS_READY, sizeof RG_EXPECTED_MS_READY);
		memcpy(fake_exe + RVA_MS_STATE_BY_NAME, RG_EXPECTED_MS_STATE_BY_NAME, sizeof RG_EXPECTED_MS_STATE_BY_NAME);
		memcpy(fake_exe + RVA_MS_MAKE_A, RG_EXPECTED_MS_MAKE_A, sizeof RG_EXPECTED_MS_MAKE_A);
		memcpy(fake_exe + RVA_MS_MAKE_B, RG_EXPECTED_MS_MAKE_B, sizeof RG_EXPECTED_MS_MAKE_B);
		memcpy(fake_exe + RVA_MS_FIND, RG_EXPECTED_MS_FIND, sizeof RG_EXPECTED_MS_FIND);
		memcpy(fake_exe + RVA_MS_STATE_BY_INDEX, RG_EXPECTED_MS_STATE_BY_INDEX, sizeof RG_EXPECTED_MS_STATE_BY_INDEX);
		memcpy(fake_exe + RVA_MS_SET_STATE, RG_EXPECTED_MS_SET_STATE, sizeof RG_EXPECTED_MS_SET_STATE);
		CHECK(!rg_verify_missions(fake_exe)); /* v4 also needs system 2's bytes */
		memcpy(fake_exe + RVA_SET_ACTIVE_HANDLER, RG_EXPECTED_SET_ACTIVE_HANDLER, sizeof RG_EXPECTED_SET_ACTIVE_HANDLER);
		memcpy(fake_exe + RVA_REPLAY_HANDLER, RG_EXPECTED_REPLAY_HANDLER, sizeof RG_EXPECTED_REPLAY_HANDLER);
		memcpy(fake_exe + RVA_MS2_LOOKUP, RG_EXPECTED_MS2_LOOKUP, sizeof RG_EXPECTED_MS2_LOOKUP);
		memcpy(fake_exe + RVA_MS2_STATE, RG_EXPECTED_MS2_STATE, sizeof RG_EXPECTED_MS2_STATE);
		memcpy(fake_exe + RVA_MS2_RESOLVE, RG_EXPECTED_MS2_RESOLVE, sizeof RG_EXPECTED_MS2_RESOLVE);
		memcpy(fake_exe + RVA_MS2_COMPONENT, RG_EXPECTED_MS2_COMPONENT, sizeof RG_EXPECTED_MS2_COMPONENT);
		CHECK(rg_verify_missions(fake_exe));
		fake_exe[RVA_START_HANDLER + 0x150] ^= 1;
		CHECK(!rg_verify_missions(fake_exe));
		fake_exe[RVA_START_HANDLER + 0x150] ^= 1;
		{ /* resolve points at the RVAs */
			rg_state r;
			memset(&r, 0, sizeof r);
			r.base = fake_exe;
			rg_resolve_missions(&r);
			CHECK(r.missions_ok && (u8 *)r.ms_manager == fake_exe + RVA_MS_MANAGER && (u8 *)r.ms_set_state == fake_exe + RVA_MS_SET_STATE);
		}

		/* not verified: nothing is called */
		RG_U32(mailbox, MB_STATUS) = RG_STATUS_READY;
		set_slot(0, "MIS_SAV_01");
		mission_req(100, RG_KIND_MISSION_MAKE_AVAILABLE, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_DONE) == 100 && RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && ms_make_calls == 0);

		/* a fake game: manager global, functions, vtable slot 0x120 */
		ms_hashes[0] = rg_hash("MIS_INTRO"); ms_hashes[1] = rg_hash("MIS_SAV_01"); ms_hashes[2] = rg_hash("MIS_ZURK_02");
		ms_states[0] = 3; ms_states[1] = 0; ms_states[2] = 1;
		fake_vtable[MS_VT_START / 8] = (u64)(void *)f_start;
		fake_mgr_global = fake_mgr_obj;
		s.missions_ok = 1;
		s.ms_manager = &fake_mgr_global;
		s.ms_alt_flag = &fake_alt_flag;
		s.ms_ready = f_ready; s.ms_state_by_name = f_state_by_name; s.ms_make_a = f_make_a; s.ms_make_b = f_make_b;
		s.ms_find = f_find; s.ms_state_by_index = f_state_by_index; s.ms_set_state = f_set_state;
		s.base = (u8 *)((u64)(void *)f_start & ~0xFFFFFull); /* the vtable entry must lie inside "the exe" */

		/* make available: 0 -> 1, both calls, the name pointer is the slot itself */
		mission_req(101, RG_KIND_MISSION_MAKE_AVAILABLE, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_BEFORE) == 0 && RG_U32(mailbox, MB_AFTER) == 1);
		CHECK(ms_make_calls == 2 && ms_last_name == (const char *)(mailbox + MB_NAMES) && RG_U32(mailbox, MB_INDEX) == 1);
		/* again: the game's action would do nothing in state 1, so neither does the helper */
		mission_req(102, RG_KIND_MISSION_MAKE_AVAILABLE, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_WRONG_STATE && ms_make_calls == 2);
		/* start: through the manager's vtable, with the flag */
		mission_req(103, RG_KIND_MISSION_START, 0, 1);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_AFTER) == 3 && RG_U32(mailbox, MB_RET) == 7);
		CHECK(ms_start_calls == 1 && ms_last_flag == 1);
		/* complete only from state 3 */
		set_slot(1, "MIS_ZURK_02");
		mission_req(104, RG_KIND_MISSION_COMPLETE, 1, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_WRONG_STATE && ms_set_calls == 0 && ms_states[2] == 1);
		set_slot(2, "MIS_INTRO");
		mission_req(105, RG_KIND_MISSION_COMPLETE, 2, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && ms_set_calls == 1 && ms_states[0] == 4 && RG_U32(mailbox, MB_AFTER) == 4);
		/* query changes nothing */
		mission_req(106, RG_KIND_MISSION_QUERY, 1, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_BEFORE) == 1 && RG_U32(mailbox, MB_AFTER) == 1);
		/* unknown mission, bad names, bad kinds, bad flag */
		set_slot(3, "MIS_NOPE");
		mission_req(107, RG_KIND_MISSION_START, 3, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_UNKNOWN_MISSION && RG_U32(mailbox, MB_INDEX) == 0xFFFFFFFFu && ms_start_calls == 1);
		memset(mailbox + MB_NAMES + 4 * RG_NAME_SIZE, 'A', RG_NAME_SIZE); /* no terminator */
		mission_req(108, RG_KIND_MISSION_QUERY, 4, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST);
		set_slot(5, "MIS BAD");
		mission_req(109, RG_KIND_MISSION_QUERY, 5, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST);
		mission_req(110, RG_KIND_MISSION_QUERY, RG_NAME_SLOTS, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST);
		mission_req(111, 99, 0, 0);   /* v6: 8-12 are kinds now */
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST);
		mission_req(112, RG_KIND_MISSION_START, 0, 2);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && ms_start_calls == 1);
		/* the other mission path, no manager, not ready: nothing called */
		fake_alt_flag = 1;
		mission_req(113, RG_KIND_MISSION_START, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_MANAGER && RG_U32(mailbox, MB_SYSTEM) == 2 && ms_start_calls == 1);
		fake_alt_flag = 0;
		fake_mgr_global = 0;
		mission_req(114, RG_KIND_MISSION_START, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_MANAGER);
		fake_mgr_global = fake_mgr_obj;
		ms_is_ready = 0;
		mission_req(115, RG_KIND_MISSION_START, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_READY && ms_start_calls == 1);
		ms_is_ready = 1;
		/* a vtable entry outside the exe is never called */
		fake_vtable[MS_VT_START / 8] = 0x10;
		mission_req(116, RG_KIND_MISSION_START, 0, 0);
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && ms_start_calls == 1);
		/* kind 0 is still the v2 give */
		RG_U32(mailbox, MB_KIND) = RG_KIND_GIVE;
		RG_U32(mailbox, MB_MODE) = 0;
		RG_U32(mailbox, MB_HERO) = 9;
		RG_U32(mailbox, MB_REQ) = 117;
		rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_SENT);

		/* ---- system 2 (your game: the flag is set) ---- */
		{
			static void *mgr2_obj[1] = { 0 };
			static void *mgr2_global = mgr2_obj;
			u64 base = (u64)(void *)f2_start & ~0xFFFFFull;
			s.base = (u8 *)base;
			for (int i = 0; i < 3; ++i) { m2_objs[i].vt = m2_vt; m2_objs[i].i = i; }
			m2_vt[MS2_VT_CAN_START / 8] = (u64)(void *)f2_can;
			m2_vt[MS2_VT_START / 8] = (u64)(void *)f2_start;
			m2_vt[MS2_VT_COMPLETE / 8] = (u64)(void *)f2_complete;
			m2_vt[MS2_VT_REPLAY / 8] = (u64)(void *)f2_replay;
			CHECK((u64)(void *)f2_can - base < RG_IMAGE_SPAN && (u64)(void *)f2_replay - base < RG_IMAGE_SPAN);
			s.ms2_manager = &mgr2_global;
			s.ms2_lookup = f2_lookup; s.ms2_state = f2_state; s.ms2_resolve = f2_resolve; s.ms2_component = f2_component;
			m2_hashes[0] = rg_hash("MIS_INTRO"); m2_hashes[1] = rg_hash("MIS_SAV_01"); m2_hashes[2] = rg_hash("MIS_ZURK_02");
			m2_states[0] = 3; m2_states[1] = 1; m2_states[2] = 0;
			fake_alt_flag = 1;
			ms_make_calls = 0;
			/* query: state through the game's function, the component, system 2 */
			mission_req(200, RG_KIND_MISSION_QUERY, 0, 0); /* slot 0 = MIS_SAV_01 */
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_BEFORE) == 1 && RG_U32(mailbox, MB_SYSTEM) == 2);
			CHECK(RG_U64(mailbox, MB_OBJECT) == (u64)&m2_objs[1] && RG_U32(mailbox, MB_INDEX) == 0x101);
			/* make available does not exist in system 2: nothing is called */
			mission_req(201, RG_KIND_MISSION_MAKE_AVAILABLE, 1, 0); /* slot 1 = MIS_ZURK_02 */
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_SUCH_ACTION && ms_make_calls == 0 && m2_states[2] == 0);
			/* start only an available (1) mission, and only when it says it can start */
			mission_req(202, RG_KIND_MISSION_START, 1, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_WRONG_STATE && m2_start_calls == 0);
			m2_can = 0;
			mission_req(203, RG_KIND_MISSION_START, 0, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_WRONG_STATE && m2_start_calls == 0 && RG_U32(mailbox, MB_RET) == 0);
			m2_can = 1;
			mission_req(204, RG_KIND_MISSION_START, 0, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && m2_start_calls == 1 && RG_U32(mailbox, MB_AFTER) == 2);
			/* complete only from 3 */
			mission_req(205, RG_KIND_MISSION_COMPLETE, 0, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_WRONG_STATE && m2_complete_calls == 0);
			mission_req(206, RG_KIND_MISSION_COMPLETE, 2, 0); /* slot 2 = MIS_INTRO */
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && m2_complete_calls == 1 && m2_states[0] == 4);
			/* replay passes the flag and 1, like the handler */
			mission_req(207, RG_KIND_MISSION_REPLAY, 1, 1);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && m2_replay_calls == 1 && m2_replay_flag == 1 && RG_U32(mailbox, MB_RET) == 1);
			/* unknown name, no manager, a vtable entry outside the exe */
			mission_req(208, RG_KIND_MISSION_QUERY, 3, 0); /* MIS_NOPE */
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_UNKNOWN_MISSION);
			m2_states[1] = 1;
			m2_vt[MS2_VT_START / 8] = 0x10;
			mission_req(209, RG_KIND_MISSION_START, 0, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && m2_start_calls == 1);
			/* ---- v6: the saved state record, walked like State() ---- */
			{
				u8 mgr_bytes[0x200];
				void *saved_resolve = (void *)s.ms2_resolve;
				u32 (*saved_state)(void *, rg_ms2_handle *) = s.ms2_state;
				r6_table_expected = (u8 *)mgr2_obj + MS2_SAVE_TABLE;
				(void)mgr_bytes;
				for (int i = 0; i < 3; ++i) {
					r6_objs[i].vt = r6_vt; r6_objs[i].i = i;
					r6_p1[i] = r6_p2[i];
					*(u64 *)(r6_p2[i] + 8) = 0xABC0 + (u64)i;
					r6_objs[i].p1 = &r6_p1[i];
					r6_entries[i].rec = &r6_records[i];
				}
				memcpy(r6_vt, m2_vt, sizeof r6_vt);
				r6_vt[MS2_VT_NODE_ID / 8] = (u64)(void *)f6_node_id;
				s.ms2_resolve = f6_resolve;
				s.ms2_state = f6_state;
				r6_records[0].state = 2; r6_records[1].state = 0; r6_records[2].state = 1;
				/* not verified yet: nothing is walked or written */
				s.state_ok = 0;
				mission_req(220, RG_KIND_MISSION_SET_STATE, 0, 1);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && r6_records[1].state == 0 && r6_table_calls == 0);
				s.state_ok = 1; s.ms2_table_find = f6_table; s.ms2_entry_find = f6_entry;
				/* probe: the record's address, nothing changed */
				mission_req(221, RG_KIND_MISSION_PROBE, 0, 0);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U64(mailbox, MB_OBJECT) == (u64)&r6_records[1].state);
				CHECK(RG_U32(mailbox, MB_BEFORE) == 0 && RG_U32(mailbox, MB_AFTER) == 0 && r6_records[1].state == 0);
				CHECK(r6_id_calls == 1 && r6_table_calls == 1 && r6_entry_calls == 1);
				/* probe takes no value */
				mission_req(222, RG_KIND_MISSION_PROBE, 0, 1);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST);
				/* set: 0 -> 1 (available), read back through State() */
				mission_req(223, RG_KIND_MISSION_SET_STATE, 0, 1);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && r6_records[1].state == 1);
				CHECK(RG_U32(mailbox, MB_BEFORE) == 0 && RG_U32(mailbox, MB_AFTER) == 1 && RG_U32(mailbox, MB_SYSTEM) == 2);
				/* values above 5 (Failed) are refused */
				mission_req(224, RG_KIND_MISSION_SET_STATE, 2, 6);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && r6_records[0].state == 2);
				/* complete finished (4) on MIS_INTRO */
				mission_req(225, RG_KIND_MISSION_SET_STATE, 2, 4);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && r6_records[0].state == 4);
				/* the walk finds nothing: not found, nothing written */
				r6_break_entry = 1;
				mission_req(226, RG_KIND_MISSION_SET_STATE, 1, 3);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_FOUND && r6_records[2].state == 1);
				r6_break_entry = 0;
				/* the walk reads something else than State(): refused */
				s.ms2_state = saved_state;   /* reads m2_states, which disagree */
				m2_states[2] = 3;
				mission_req(227, RG_KIND_MISSION_SET_STATE, 1, 0);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && r6_records[2].state == 1);
				s.ms2_state = f6_state;
				/* node id outside the exe: refused */
				r6_vt[MS2_VT_NODE_ID / 8] = 0x10;
				mission_req(228, RG_KIND_MISSION_SET_STATE, 1, 0);
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_FOUND && r6_records[2].state == 1);
				r6_vt[MS2_VT_NODE_ID / 8] = (u64)(void *)f6_node_id;
				s.ms2_resolve = (rg_ms2_resolve_fn)saved_resolve;
				s.ms2_state = saved_state;
			}
			/* ---- v6: the level mask and the travel byte ---- */
			{
				memset(l6_levels, 0, sizeof l6_levels);
				*(u32 *)(l6_levels + 0x30) = 0x6;     /* levels 1 and 2 */
				*(u32 *)(l6_levels + 0x2C) = 0x2;
				*(u32 *)(l6_levels + 0x20) = 2;
				s.levels_ok = 0;
				RG_U32(mailbox, MB_KIND) = RG_KIND_LEVEL_SET; RG_U32(mailbox, MB_FLAG) = 1; RG_U32(mailbox, MB_COUNT) = 4;
				RG_U32(mailbox, MB_REQ) = 240;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_DONE) == 240 && RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && l6_set_calls == 0);
				s.levels_ok = 1; s.levels = l6_levels; s.level_set = f6_level_set;
				RG_U32(mailbox, MB_REQ) = 241;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_BEFORE) == 0x6 && RG_U32(mailbox, MB_AFTER) == 0x16);
				CHECK(RG_U32(mailbox, MB_RET) == 0x2 && RG_U32(mailbox, MB_INDEX) == 2 && l6_set_calls == 1);
				/* levels outside 1..10 are refused, like the action does */
				RG_U32(mailbox, MB_COUNT) = 11; RG_U32(mailbox, MB_REQ) = 242;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && l6_set_calls == 1);
				RG_U32(mailbox, MB_COUNT) = 0; RG_U32(mailbox, MB_REQ) = 243;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && l6_set_calls == 1);
				/* lock */
				RG_U32(mailbox, MB_COUNT) = 1; RG_U32(mailbox, MB_FLAG) = 0; RG_U32(mailbox, MB_REQ) = 244;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_AFTER) == 0x14);
				/* read */
				RG_U32(mailbox, MB_KIND) = RG_KIND_LEVEL_READ; RG_U32(mailbox, MB_REQ) = 245;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_BEFORE) == 0x14 && RG_U32(mailbox, MB_AFTER) == 0x14);
				/* travel byte */
				s.travel_ok = 0;
				RG_U32(mailbox, MB_KIND) = RG_KIND_TRAVEL_SET; RG_U32(mailbox, MB_FLAG) = 1; RG_U32(mailbox, MB_REQ) = 246;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && l6_travel == 0);
				s.travel_ok = 1; s.travel_byte = &l6_travel;
				RG_U32(mailbox, MB_REQ) = 247;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_BEFORE) == 0 && RG_U32(mailbox, MB_AFTER) == 1 && l6_travel == 1);
				RG_U32(mailbox, MB_FLAG) = 2; RG_U32(mailbox, MB_REQ) = 248;
				rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
				CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && l6_travel == 1);
				RG_U32(mailbox, MB_FLAG) = 0;
			}
			mgr2_global = 0;
			mission_req(210, RG_KIND_MISSION_QUERY, 0, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_MANAGER);
			fake_alt_flag = 0;
			/* replay does not exist in system 1 */
			mission_req(211, RG_KIND_MISSION_REPLAY, 0, 0);
			rg_pump(&s, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
			CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_SUCH_ACTION && RG_U32(mailbox, MB_SYSTEM) == 1);
		}
	}

	/* ---- v5: armor through VanityGiveBundleAction's path ---- */
	{
		CHECK(!rg_verify_vanity(fake_exe));
		memcpy(fake_exe + RVA_VANITY_GIVE_HANDLER, RG_EXPECTED_VANITY_GIVE_HANDLER, sizeof RG_EXPECTED_VANITY_GIVE_HANDLER);
		memcpy(fake_exe + RVA_RESOLVE_HANDLE, RG_EXPECTED_RESOLVE_HANDLE, sizeof RG_EXPECTED_RESOLVE_HANDLE);
		memcpy(fake_exe + RVA_FIND_COMPONENT_A, RG_EXPECTED_FIND_COMPONENT_A, sizeof RG_EXPECTED_FIND_COMPONENT_A);
		memcpy(fake_exe + RVA_FIND_COMPONENT_B, RG_EXPECTED_FIND_COMPONENT_B, sizeof RG_EXPECTED_FIND_COMPONENT_B);
		CHECK(!rg_verify_vanity(fake_exe));
		memcpy(fake_exe + RVA_VANITY_GIVE_BUNDLE, RG_EXPECTED_VANITY_GIVE_BUNDLE, sizeof RG_EXPECTED_VANITY_GIVE_BUNDLE);
		CHECK(!rg_verify_vanity(fake_exe));                 /* v5: the output plug function too */
		memcpy(fake_exe + RVA_FIRE_OUTPUT, RG_EXPECTED_FIRE_OUTPUT, sizeof RG_EXPECTED_FIRE_OUTPUT);
		CHECK(rg_verify_vanity(fake_exe));
		fake_exe[RVA_VANITY_GIVE_HANDLER + 0x0C] ^= 1;      /* the hero-handle displacement */
		CHECK(!rg_verify_vanity(fake_exe));
		fake_exe[RVA_VANITY_GIVE_HANDLER + 0x0C] ^= 1;
		{
			rg_state r;
			memset(&r, 0, sizeof r);
			r.base = fake_exe;
			rg_resolve_vanity(&r);
			CHECK(r.vanity_ok && (u8 *)r.vanity_give == fake_exe + RVA_VANITY_GIVE_BUNDLE &&
			      (u8 *)r.resolve_handle == fake_exe + RVA_RESOLVE_HANDLE && (u8 *)r.fire == fake_exe + RVA_FIRE_OUTPUT);
		}
		rg_state v;
		memset(&v, 0, sizeof v);
		v.mailbox = mailbox;
		v.base = fake_exe;
		*(u32 *)(fake_exe + RVA_HERO_HANDLE) = 0x00512345;
		RG_U32(mailbox, MB_STATUS) = RG_STATUS_READY;
		/* not verified: nothing is called */
		vanity_req(300, 0x8001C43CEBA5E2FAull);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_DONE) == 300 && RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && v_give_calls == 0);
		v.vanity_ok = 1;
		v.resolve_handle = fv_resolve; v.find_component_a = fv_find_a; v.find_component_b = fv_find_b; v.vanity_give = fv_give;
		/* component list B (word at +0x88 is 0), bundle passed with flag 0, answer reported */
		vanity_req(301, 0x8001C43CEBA5E2FAull);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_RET) == 1 && v_give_calls == 1);
		CHECK(v_hero_handle_seen == 0x00512345 && v_list_used == 0x58 && v_type_seen == fake_exe + RVA_VANITY_MANAGER_TYPE);
		CHECK(v_last_bundle == 0x8001C43CEBA5E2FAull && v_last_flag == 0);
		/* the same piece again: the game says no (owned) */
		vanity_req(302, 0x8001C43CEBA5E2FAull);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U32(mailbox, MB_RET) == 0 && v_give_calls == 2);
		/* component list A when the word at +0x88 is non-zero */
		*(unsigned short *)(v_actor.raw + 0x88) = 3;
		vanity_req(303, 0x84302A735518B94Cull);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RET) == 1 && v_list_used == 0x80);
		/* no hero, no manager, a zero bundle: nothing given */
		v_no_actor = 1;
		vanity_req(304, 0x84302A735518B94Dull);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_TARGET && v_give_calls == 3);
		v_no_actor = 0; v_no_mgr = 1;
		vanity_req(305, 0x84302A735518B94Dull);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_NO_TARGET && v_give_calls == 3);
		v_no_mgr = 0;
		vanity_req(306, 0);
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_BAD_REQUEST && v_give_calls == 3);
		/* the same request is not handled twice */
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(v_give_calls == 3);
		(void)v_base;
	}

	/* v5: armor sources - rg_armor_decide, as the replaced VanityGiveBundleAction runs it */
	{
		rg_state v;
		u8 node[0x70];
		static u8 fake_exe2[0x7000000];
		memset(&v, 0, sizeof v);
		memset(mailbox, 0x5A, sizeof mailbox);
		rg_mailbox_init(mailbox, fake_exe2);
		CHECK(RG_U32(mailbox, MB_ARMOR_ON) == 0 && RG_U32(mailbox, MB_ARMOR_SEQ) == 0 && RG_U64(mailbox, MB_ARMOR_TABLE) == 0);
		CHECK(RG_U64(mailbox, MB_ARMOR_RING) == 0 && mailbox[MB_NAMES] == 0x5A); /* names are left alone */
		v.mailbox = mailbox; v.base = fake_exe2;
		*(u32 *)(fake_exe2 + RVA_HERO_HANDLE) = 0x00512345;
		v.vanity_ok = 1;
		v.resolve_handle = fv_resolve; v.find_component_a = fv_find_a; v.find_component_b = fv_find_b; v.vanity_give = fv_give;
		v.fire = fv_fire;
		*(unsigned short *)(v_actor.raw + 0x88) = 0;
		v_owned_mask = 0; v_give_calls = 0;
		memset(node, 0, sizeof node);
		*(u64 *)(node + 0x58) = 0x1234;
		*(u64 *)(node + 0x60) = 0x8000000000000005ull;
		/* nothing listed: given exactly like the game, success, noted in the ring */
		CHECK(rg_armor_decide(&v, node) == RG_PLUG_SUCCESS && v_give_calls == 1 && v_last_bundle == 0x8000000000000005ull);
		CHECK(RG_U32(mailbox, MB_ARMOR_SEQ) == 1 && RG_U32(mailbox, MB_ARMOR_CALLS) == 1);
		CHECK(RG_U64(mailbox, MB_ARMOR_RING + 16) == 0x8000000000000005ull && RG_U32(mailbox, MB_ARMOR_RING + 16 + 8) == 1 &&
		      RG_U32(mailbox, MB_ARMOR_RING + 16 + 12) == RG_ARMOR_GIVEN);
		/* owned already: the game says no, failure plug */
		CHECK(rg_armor_decide(&v, node) == RG_PLUG_FAILURE && v_give_calls == 2);
		CHECK(RG_U32(mailbox, MB_ARMOR_RING + 32 + 12) == RG_ARMOR_NOT_GIVEN);
		/* listed but interception off: given */
		*(u64 *)(node + 0x60) = 0x8000000000000006ull;
		RG_U64(mailbox, MB_ARMOR_TABLE + 8 * 7) = 0x8000000000000006ull;
		CHECK(rg_armor_decide(&v, node) == RG_PLUG_SUCCESS && v_give_calls == 3);
		/* listed and on: nothing given, entry cleared, success, ring says intercepted */
		*(u64 *)(node + 0x60) = 0x8000000000000007ull;
		RG_U64(mailbox, MB_ARMOR_TABLE + 8 * 47) = 0x8000000000000007ull;
		RG_U32(mailbox, MB_ARMOR_ON) = 1;
		CHECK(rg_armor_decide(&v, node) == RG_PLUG_SUCCESS && v_give_calls == 3);
		CHECK(RG_U64(mailbox, MB_ARMOR_TABLE + 8 * 47) == 0 && RG_U64(mailbox, MB_ARMOR_TABLE + 8 * 7) == 0x8000000000000006ull);
		CHECK(RG_U32(mailbox, MB_ARMOR_SEQ) == 4 && RG_U32(mailbox, MB_ARMOR_RING + 64 + 12) == RG_ARMOR_INTERCEPTED &&
		      RG_U64(mailbox, MB_ARMOR_RING + 64) == 0x8000000000000007ull);
		/* the same source again (a replay, a second visit): the entry is gone, so it is given */
		CHECK(rg_armor_decide(&v, node) == RG_PLUG_SUCCESS && v_give_calls == 4);
		/* a zero bundle is never intercepted, even with a zero... nothing listed as 0 matches */
		*(u64 *)(node + 0x60) = 0;
		CHECK(rg_armor_decide(&v, node) == RG_PLUG_FAILURE);
		/* the ring wraps: entry = seq % 16, and seq only counts up */
		for (int i = 0; i < 20; ++i) rg_armor_decide(&v, node);
		CHECK(RG_U32(mailbox, MB_ARMOR_SEQ) == 26 && RG_U32(mailbox, MB_ARMOR_RING + 16 * (26 % RG_ARMOR_RING) + 8) == 26);
		CHECK(MB_ARMOR_TABLE + 8 * RG_ARMOR_MAX <= MB_ARMOR_RING && MB_ARMOR_RING + 16 * RG_ARMOR_RING <= MB_NAMES);
		CHECK(MB_CONFIG_SIGS + 4 <= MB_ARMOR_TABLE && MB_ARMOR_ON >= MB_CLEAR_END);
		(void)fire_calls; (void)fire_plug; (void)fire_ctx;
	}

	/* v5: config lookup, walked like rivet_hook's configs::find */
	{
		rg_state v;
		static u8 mgr[0x70];
		static u8 entries[5 * 0x40];
		u64 obj = 0;
		memset(&v, 0, sizeof v);
		memset(mailbox, 0, sizeof mailbox);
		v.mailbox = mailbox;
		RG_U32(mailbox, MB_STATUS) = RG_STATUS_READY;
		/* no manager */
		RG_U32(mailbox, MB_KIND) = RG_KIND_CONFIG_LOOKUP; RG_U64(mailbox, MB_ITEM) = 0xAE5CE1E22662E244ull; RG_U32(mailbox, MB_REQ) = 500;
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_DONE) == 500 && RG_U32(mailbox, MB_RESULT) == RG_RESULT_NOT_VERIFIED && RG_U64(mailbox, MB_OBJECT) == 0);
		v.config_mgr = mgr;
		*(u8 **)(mgr + CFG_ENTRIES) = entries;
		*(u64 *)(mgr + CFG_STRIDE) = 0x40;
		*(int *)(mgr + CFG_MAX) = 5;
		/* entry 1: same id but not loaded; entry 3: loaded */
		*(u64 *)(entries + 0x40 + CFG_ENTRY_ID) = 0xAE5CE1E22662E244ull; entries[0x40] = 2;
		*(u64 *)(entries + 0x40 + CFG_ENTRY_OBJECT) = 0x1111;
		*(u64 *)(entries + 0xC0 + CFG_ENTRY_ID) = 0xAE5CE1E22662E244ull; entries[0xC0] = CFG_STATE_LOADED;
		*(u64 *)(entries + 0xC0 + CFG_ENTRY_OBJECT) = 0x7FF612345678ull;
		RG_U32(mailbox, MB_REQ) = 501;
		rg_pump(&v, direct_give, direct_mission, direct_vanity, direct_lookup, direct_level);
		CHECK(RG_U32(mailbox, MB_RESULT) == RG_RESULT_DONE && RG_U64(mailbox, MB_OBJECT) == 0x7FF612345678ull);
		CHECK(rg_config_lookup(&v, 0x1234, &obj) == RG_RESULT_NOT_FOUND && obj == 0);
		CHECK(rg_config_lookup(&v, 0, &obj) == RG_RESULT_BAD_REQUEST);
		*(u64 *)(mgr + CFG_STRIDE) = 0x10; /* nonsense layout: refused */
		CHECK(rg_config_lookup(&v, 0xAE5CE1E22662E244ull, &obj) == RG_RESULT_NOT_READY);
	}

	/* v5: the config-manager signature, with its rel32 */
	{
		static u8 code[0x400];
		u32 m = 0;
		u8 *found;
		memset(code, 0xCC, sizeof code);
		CHECK(rg_find_config_manager(code, sizeof code, &m) == 0 && m == 0);
		memcpy(code + 0x100, RG_CONFIG_SIGNATURE, sizeof RG_CONFIG_SIGNATURE);
		*(int *)(code + 0x100 + RG_CONFIG_REL) = -0x80;   /* a negative displacement, as rivet_hook warns */
		found = rg_find_config_manager(code, sizeof code, &m);
		CHECK(m == 1 && found == code + 0x100 + RG_CONFIG_REL + 4 - 0x80);
		memcpy(code + 0x300, RG_CONFIG_SIGNATURE, sizeof RG_CONFIG_SIGNATURE);
		*(int *)(code + 0x300 + RG_CONFIG_REL) = 0x10;
		found = rg_find_config_manager(code, sizeof code, &m);
		CHECK(m == 2 && found == code + 0x100 + RG_CONFIG_REL + 4 - 0x80); /* the first, like rivet_hook */
		/* a match cut off by the end of the section is not read */
		CHECK(rg_find_config_manager(code + 0x300, 0x24, &m) == 0);
	}

	/* v7: the SceneManager by rivet_hook's SCENE_MANAGER signature (?? bytes are wildcards) */
	{
		static u8 code[0x400];
		static const u8 hit[15] = { 0x48, 0x8D, 0x0D, 0x11, 0x22, 0x33, 0x44, 0xE8, 0x55, 0x66, 0x77, 0x88, 0x48, 0x63, 0x75 };
		u32 m = 9;
		u8 *found;
		memset(code, 0xCC, sizeof code);
		CHECK(rg_find_scene_manager(code, sizeof code, &m) == 0 && m == 0);
		memcpy(code + 0x40, hit, sizeof hit);
		*(int *)(code + 0x40 + RG_SCENE_REL) = -0x20;      /* lea rcx, [rip - 0x20] */
		found = rg_find_scene_manager(code, sizeof code, &m);
		CHECK(m == 1 && found == code + 0x40 + 7 - 0x20);
		code[0x40 + 14] = 0x76;                            /* a fixed byte differs: no match */
		CHECK(rg_find_scene_manager(code, sizeof code, &m) == 0 && m == 0);
		code[0x40 + 14] = 0x75;
		memcpy(code + 0x200, hit, sizeof hit);              /* two matches: the caller publishes nothing */
		found = rg_find_scene_manager(code, sizeof code, &m);
		CHECK(m == 2 && found == code + 0x40 + 7 - 0x20);
		CHECK(rg_find_scene_manager(code + 0x200, 14, &m) == 0 && m == 0);   /* cut off */
	}

	/* the give count: currency comes with big counts */
	{
		rg_state g;
		u32 t = 0, pth = 0;
		memset(&g, 0, sizeof g);
		g.send = fake_send; g.get_players = fake_get_players;
		static u64 msg = 0x99;
		g.message = &msg;
		CHECK(rg_give(&g, 0x95FFA4C1254A6F29ull, 5000, 77, 0, &t, &pth) == RG_RESULT_SENT && sent_count == 5000);
		CHECK(rg_give(&g, 0x95FFA4C1254A6F29ull, RG_MAX_COUNT + 1, 77, 0, &t, &pth) == RG_RESULT_BAD_REQUEST);
	}

	/* the hook bytes */
	{
		u8 code[32], tramp[32];
		memcpy(code, RG_EXPECTED_PUMP, 32);
		rg_build_trampoline(tramp, code);
		CHECK(memcmp(tramp, RG_EXPECTED_PUMP, HOOK_BYTES) == 0);
		CHECK(tramp[14] == 0xFF && tramp[15] == 0x25 && *(u64 *)(tramp + 20) == (u64)(code + HOOK_BYTES));
		rg_write_jump(code, 0x1122334455667788ULL);
		CHECK(code[0] == 0xFF && code[1] == 0x25 && *(u64 *)(code + 6) == 0x1122334455667788ULL);
		CHECK(rg_is_boundary(0) && rg_is_boundary(5) && rg_is_boundary(6) && rg_is_boundary(10));
		CHECK(!rg_is_boundary(1) && !rg_is_boundary(13));
	}

	printf(failures ? "%d FAILED\n" : "all native core checks passed\n", failures);
	return failures != 0;
}
