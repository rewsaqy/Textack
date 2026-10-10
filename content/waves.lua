-- Enemy data (mirrors textack/core/enemies.py; formulas live in worker.lua).
-- Cross-checked against core on waves 1..30 by tests/test_lua_content.py.
return {
  tiers = {
    { upto = 2, name = "SCOUT", interval = 6.5, dmg = 6, burst = 1,
      hp_base = 60, hp_wave = 35, proj = "▼", col = "yellow" },
    { upto = 4, name = "RAIDER", interval = 5.2, dmg = 8, burst = 1,
      hp_base = 70, hp_wave = 42, proj = "●", col = "yellow" },
    { upto = 6, name = "GOLEM", interval = 4.3, dmg = 10, burst = 2,
      hp_base = 80, hp_wave = 48, proj = "✦", col = "red" },
    { upto = math.huge, name = "OVERLORD", interval = 3.5, dmg = 12,
      burst = 3, hp_base = 90, hp_wave = 55, proj = "✹", col = "red" },
  },
  boss_every = 5,
  boss_interval_mult = 0.85,
  boss_dmg_add = 3,
  boss_max_burst = 4,
  boss_hp_mult = 1.7,
  min_interval = 2.6,
  late_wave = 7,
  late_step = 0.12,
}
