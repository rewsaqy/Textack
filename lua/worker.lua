-- Content worker (phase 4): dialog, waves, words + hot-reload over stdio.
--
-- Usage: lua worker.lua [--content DIR]
-- Speaks protocol v1, content domain (docs/PROTOCOL.md). Owns DATA only;
-- math-heavy sim stays in Rust/Python. On content-reload with broken
-- files the old version keeps serving and errors are reported as data.
-- Limitations (documented, tested): integers must satisfy |v| < 2^53
-- (doubles), seeds < 2^53.
local HERE = (debug.getinfo(1, "S").source:match("@(.*/)") or "./")
package.path = HERE .. "?.lua;" .. package.path

local json = require("json")
local mt = require("mt")

local state = { dir = HERE .. "../content", version = 0, data = nil }

do
  local args = arg or {}
  for i = 1, #args do
    if args[i] == "--content" and args[i + 1] then
      state.dir = args[i + 1]
    else
      local d = args[i]:match("^%-%-content=(.+)$")
      if d then state.dir = d end
    end
  end
end

-- ---------- validation (worker-side minimal; proto.py is normative) ----------

local function is_int(x)
  return type(x) == "number" and x == x and x ~= math.huge
     and x ~= -math.huge and x % 1 == 0 and math.abs(x) < 2 ^ 53
end

local function is_num(x)
  return type(x) == "number" and x == x and x ~= math.huge and x ~= -math.huge
end

local function is_str(x) return type(x) == "string" end

local function err(code, msg, id)
  local e = { v = 1, t = "error", code = code }
  if msg then e.msg = msg end
  if id ~= nil and id ~= json.null then e.id = id end
  return e
end

local function echo_id(m)
  local id = m.id
  if id == nil or id == json.null then return nil end
  return id
end

local function need_id(m, what)
  local id = echo_id(m)
  if id == nil then return nil, err("bad-message", what .. " needs id") end
  return id, nil
end

-- ---------- content loading ----------

local function load_content(dir)
  local errs = {}
  local function loadf(name)
    local chunk, e = loadfile(dir .. "/" .. name .. ".lua")
    if not chunk then
      errs[#errs + 1] = name .. ": " .. (e or "cannot read")
      return nil
    end
    local ok, val = pcall(chunk)
    if not ok then
      errs[#errs + 1] = name .. ": " .. tostring(val)
      return nil
    end
    if type(val) ~= "table" then
      errs[#errs + 1] = name .. ": must return a table"
      return nil
    end
    return val
  end
  local waves, dialog, words = loadf("waves"), loadf("dialog"), loadf("words")
  if #errs == 0 then
    if type(waves.tiers) ~= "table" or type(dialog.waifus) ~= "table"
       or type(words.tier1) ~= "table" then
      errs[#errs + 1] = "shape: tiers/waifus/tier1 missing"
    end
  end
  if #errs > 0 then return nil, errs end
  return { waves = waves, dialog = dialog, words = words }, errs
end

-- ---------- content queries ----------

local live = mt.from_seed(os.time() % 2147483647)

local function get_waifu(wid)
  local w = state.data.dialog.waifus[wid]
  if type(w) ~= "table" then w = state.data.dialog.waifus.aika end
  return w
end

local function pool_of(w, trigger)
  local p = w[trigger]
  if type(p) ~= "table" or #p == 0 then p = w.idle end
  return p
end

local function fill(line, wave, enemy)
  local wv = wave ~= nil and tostring(wave) or "?"
  line = line:gsub("{wave}", function() return wv end)
  return line:gsub("{enemy}", function() return enemy or "enemy" end)
end

local function wave_cfg(wave)
  local W = state.data.waves
  local t = nil
  for _, tier in ipairs(W.tiers) do
    if wave <= tier.upto then t = tier; break end
  end
  t = t or W.tiers[#W.tiers]
  local name, interval, dmg, burst = t.name, t.interval, t.dmg, t.burst
  local hp = t.hp_base + wave * t.hp_wave
  local boss = (wave % W.boss_every == 0)
  if boss then
    name = "BOSS " .. name
    interval = math.max(W.min_interval, interval * W.boss_interval_mult)
    dmg = dmg + W.boss_dmg_add
    burst = math.min(W.boss_max_burst, burst + 1)
    hp = math.floor(hp * W.boss_hp_mult)
  end
  interval = math.max(W.min_interval,
                      interval - math.max(0, wave - W.late_wave) * W.late_step)
  return { name = name, interval = interval, dmg = dmg, burst = burst,
           hp = hp, proj = t.proj, col = t.col, boss = boss }
end

local function word_pool(wave)
  local W = state.data.words
  local pool = {}
  local function add(t) for _, w in ipairs(t) do pool[#pool + 1] = w end end
  add(W.tier1)
  if wave >= 2 then add(W.tier2) end
  if wave >= 3 then add(W.tier3) end
  return pool
end

-- ---------- dispatch ----------

local handlers = {}

handlers.hello = function(m)
  local r = { v = 1, t = "ready", role = "content-lua", proto = 1 }
  local id = echo_id(m)
  if id ~= nil then r.id = id end
  return r
end

handlers.ping = function(m)
  local r = { v = 1, t = "pong" }
  local id = echo_id(m)
  if id ~= nil then r.id = id end
  return r
end

handlers.bye = function(m) return { v = 1, t = "bye" } end

handlers.dialog = function(m)
  local id, e = need_id(m, "dialog")
  if not id then return e end
  if not is_str(m.wid) or not is_str(m.trigger) then
    return err("bad-message", "dialog fields", id)
  end
  local wave, enemy = m.wave, m.enemy
  if wave ~= nil and wave ~= json.null and not is_int(wave) then
    return err("bad-message", "dialog wave", id)
  end
  if enemy ~= nil and enemy ~= json.null and not is_str(enemy) then
    return err("bad-message", "dialog enemy", id)
  end
  if wave == json.null then wave = nil end
  if enemy == json.null then enemy = nil end
  local seed = m.seed
  if seed == nil or seed == json.null then seed = 0 end
  if not is_int(seed) or seed < 0 then
    return err("bad-message", "bad seed", id)
  end
  local w = get_waifu(m.wid)
  local p = pool_of(w, m.trigger)
  return { v = 1, t = "line", id = id,
           text = fill(p[(seed % #p) + 1], wave, enemy) }
end

handlers.mood = function(m)
  local id, e = need_id(m, "mood")
  if not id then return e end
  if not is_str(m.wid) or not is_str(m.mood) then
    return err("bad-message", "mood fields", id)
  end
  local seed = m.seed
  if seed == nil or seed == json.null then seed = 0 end
  if not is_int(seed) or seed < 0 then
    return err("bad-message", "bad seed", id)
  end
  local w = get_waifu(m.wid)
  local p = w[m.mood]
  if type(p) ~= "table" or #p == 0 then p = w.idle end
  return { v = 1, t = "line", id = id, text = p[(seed % #p) + 1] }
end

handlers.wave = function(m)
  local id, e = need_id(m, "wave")
  if not id then return e end
  if not is_int(m.wave) then return err("bad-message", "wave fields", id) end
  local c = wave_cfg(m.wave)
  return { v = 1, t = "wave-cfg", id = id, name = c.name,
           interval = c.interval, dmg = c.dmg, burst = c.burst, hp = c.hp,
           proj = c.proj, col = c.col, boss = c.boss }
end

handlers.unlocks = function(m)
  local id, e = need_id(m, "unlocks")
  if not id then return e end
  if type(m.unlocked) ~= "table" or not is_int(m.wave) then
    return err("bad-message", "unlocks fields", id)
  end
  local have = {}
  -- mirror core.check_unlocks: an empty list means a fresh player (aika)
  if #m.unlocked == 0 then have.aika = true end
  for _, u in ipairs(m.unlocked) do have[u] = true end
  local D = state.data.dialog
  local ids = json.array()
  for _, wid in ipairs(D.order) do
    if not have[wid] and m.wave >= (D.unlock_wave[wid] or 999) then
      ids[#ids + 1] = wid
    end
  end
  return { v = 1, t = "unlocks-is", id = id, ids = ids }
end

handlers.pick = function(m)
  local id, e = need_id(m, "pick")
  if not id then return e end
  if not is_int(m.wave) then return err("bad-message", "pick fields", id) end
  local seed = m.seed
  if seed == nil or seed == json.null then seed = nil end
  if seed ~= nil and (not is_int(seed) or seed < 0) then
    return err("bad-message", "bad seed", id)
  end
  local pool = word_pool(m.wave)
  local idx
  if seed ~= nil then
    idx = mt.choice_index(mt.from_seed(seed), #pool)
  else
    idx = mt.choice_index(live, #pool)
  end
  return { v = 1, t = "word", id = id, text = pool[idx] }
end

handlers["content-reload"] = function(m)
  local dir = state.dir
  if m.path ~= nil and m.path ~= json.null then
    if not is_str(m.path) then
      return err("bad-message", "reload path", echo_id(m))
    end
    dir = m.path
  end
  local data, errs = load_content(dir)
  local rep = { v = 1, t = "content-state" }
  local id = echo_id(m)
  if id ~= nil then rep.id = id end
  if data then
    state.data, state.dir = data, dir
    state.version = state.version + 1
    rep.version, rep.errors = state.version, json.array()
  else
    rep.version, rep.errors = state.version, json.array()
    for _, x in ipairs(errs) do rep.errors[#rep.errors + 1] = x end
  end
  return rep
end

local function handle(m)
  if type(m) ~= "table" then
    return err("bad-envelope", "message must be an object")
  end
  if m.v ~= 1 then return err("bad-version", "v must be 1") end
  if not is_str(m.t) then return err("unknown-type", "missing t", echo_id(m)) end
  local h = handlers[m.t]
  if not h then return err("unknown-type", "unknown t", echo_id(m)) end
  local ok, rep = pcall(h, m)
  if not ok then return err("internal", "worker fault", echo_id(m)) end
  return rep
end

-- ---------- boot + stdio loop ----------

local boot, berrs = load_content(state.dir)
if not boot then
  io.stderr:write("content: " .. table.concat(berrs, "; ") .. "\n")
  os.exit(1)
end
state.data = boot
state.version = 1
io.stdout:setvbuf("line")

while true do
  local line = io.read("*l")
  if line == nil then break end -- EOF
  if not line:match("^%s*$") then
    local ok, msg = pcall(json.decode, line)
    if ok then
      local rep = handle(msg)
      if rep ~= nil then
        local wok, out = pcall(json.encode, rep)
        if wok then
          io.write(out .. "\n")
          io.flush()
        end
      end
    end
    -- unparseable lines carry no envelope: skipped, never answered
  end
end
