-- MT19937 twin of CPython's `random`, in pure arithmetic Lua (no bitops:
-- exact on both 5.4 integers/floats and LuaJIT doubles, all state < 2^53).
-- Seeding, random(), getrandbits, randbelow, shuffle, choice_index all
-- mirror CPython exactly. Proven by tests/test_lua_content.py against
-- live Python vectors. Limitation: seeds must be < 2^53 (doubles cannot
-- hold bigger seeds exactly); protocol seeds beyond that are rejected.
local M = {}
local N, MAG, MA = 624, 397, 0x9908b0df
local U32 = 4294967296

local function add32(a, b) return (a + b) % U32 end

local function mul32(a, b)
  local ah, al = math.floor(a / 65536), a % 65536
  local bh, bl = math.floor(b / 65536), b % 65536
  local mid = (ah * bl + al * bh) % 65536
  return (mid * 65536 + al * bl) % U32
end

local function rshift32(a, k) return math.floor(a / (2 ^ k)) end
local function lshift32(a, k) return (a * (2 ^ k)) % U32 end

local function bitop(a, b, want_both)
  local r, m = 0, 1
  for _ = 1, 32 do
    local ab, bb = a % 2, b % 2
    if want_both then
      if ab == 1 and bb == 1 then r = r + m end
    else
      if ab ~= bb then r = r + m end
    end
    a = math.floor(a / 2); b = math.floor(b / 2); m = m * 2
  end
  return r
end

local function band32(a, b) return bitop(a, b, true) end
local function bxor32(a, b) return bitop(a, b, false) end

local function init_genrand(mt, s)
  mt[1] = s
  for i = 2, N do
    local p = mt[i - 1]
    mt[i] = add32(mul32(1812433253, bxor32(p, rshift32(p, 30))), i - 1)
  end
end

function M.from_words(key) -- key: 1-based array of uint32, non-empty
  local mt = {}
  init_genrand(mt, 19650218)
  local klen = #key
  local i, j = 2, 1
  local k = math.max(N, klen)
  for _ = 1, k do
    local p = mt[i - 1]
    mt[i] = add32(add32(bxor32(mt[i], mul32(bxor32(p, rshift32(p, 30)), 1664525)), key[j]), j - 1)
    i, j = i + 1, j + 1
    if i > N then mt[1] = mt[N]; i = 2 end
    if j > klen then j = 1 end
  end
  for _ = 1, N - 1 do
    local p = mt[i - 1]
    mt[i] = (bxor32(mt[i], mul32(bxor32(p, rshift32(p, 30)), 1566083941)) - (i - 1)) % U32
    i = i + 1
    if i > N then mt[1] = mt[N]; i = 2 end
  end
  mt[1] = 0x80000000
  return { mt = mt, index = N + 1 }
end

function M.from_seed(seed) -- seed: non-negative integer < 2^53
  local words = {}
  local s = seed
  repeat
    words[#words + 1] = s % U32
    s = math.floor(s / U32)
  until s == 0
  return M.from_words(words)
end

local function twist(st)
  local mt = st.mt
  for i = 1, N do
    local i1 = (i % N) + 1
    local im = ((i + MAG - 1) % N) + 1
    local hi = mt[i] >= 0x80000000 and 0x80000000 or 0
    local x = hi + (mt[i1] % 0x80000000)
    local xa = math.floor(x / 2)
    if x % 2 == 1 then xa = bxor32(xa, MA) end
    mt[i] = bxor32(mt[im], xa)
  end
  st.index = 1
end

local function gen(st)
  if st.index > N then twist(st) end
  local y = st.mt[st.index]
  st.index = st.index + 1
  y = bxor32(y, rshift32(y, 11))
  y = bxor32(y, band32(lshift32(y, 7), 0x9d2c5680))
  y = bxor32(y, band32(lshift32(y, 15), 0xefc60000))
  y = bxor32(y, rshift32(y, 18))
  return y
end

function M.genrand(st) return gen(st) end

function M.random(st)
  local a = math.floor(gen(st) / 32)
  local b = math.floor(gen(st) / 64)
  return (a * 67108864 + b) / 9007199254740992
end

function M.getrandbits(st, k)
  if k == 0 then return 0 end
  assert(k <= 32, "getrandbits limited to 32 bits")
  local words = math.floor((k - 1) / 32) + 1
  local r = 0
  for _ = 1, words do r = r * U32 + gen(st) end
  return math.floor(r / (2 ^ (words * 32 - k)))
end

local function bitlen(n)
  local k = 0
  while n > 0 do k = k + 1; n = math.floor(n / 2) end
  return k
end

function M.randbelow(st, n)
  assert(n > 0)
  local k = bitlen(n)
  while true do
    local r = M.getrandbits(st, k)
    if r < n then return r end
  end
end

function M.shuffle(st, t)
  for i = #t, 2, -1 do
    local j = M.randbelow(st, i) + 1
    t[i], t[j] = t[j], t[i]
  end
end

function M.choice_index(st, n) return M.randbelow(st, n) + 1 end

return M
