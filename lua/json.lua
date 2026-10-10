-- Minimal JSON for protocol v1 (5.1/5.4 compatible: no bitops, no goto,
-- no utf8 lib, no table.pack). Decoded arrays are marked (see array());
-- the encoder emits object keys sorted for stable output.
local json = {}
json.null = setmetatable({}, { __tostring = function() return "null" end })

local function u8(cp)
  if cp < 0x80 then
    return string.char(cp)
  elseif cp < 0x800 then
    return string.char(0xC0 + math.floor(cp / 64), 0x80 + (cp % 64))
  elseif cp < 0x10000 then
    return string.char(0xE0 + math.floor(cp / 4096),
                       0x80 + (math.floor(cp / 64) % 64), 0x80 + (cp % 64))
  else
    return string.char(0xF0 + math.floor(cp / 262144),
                       0x80 + (math.floor(cp / 4096) % 64),
                       0x80 + (math.floor(cp / 64) % 64), 0x80 + (cp % 64))
  end
end

function json.array(t)
  t = t or {}
  return setmetatable(t, { __jsontype = "array" })
end

function json.is_array(t)
  local m = getmetatable(t)
  return type(t) == "table" and m ~= nil and m.__jsontype == "array"
end

function json.decode(s)
  local pos = 1
  local function err(msg) error("json: " .. msg .. " at " .. pos) end
  local function skip()
    while pos <= #s and s:sub(pos, pos):match("%s") do pos = pos + 1 end
  end
  local parse_value
  local function parse_string()
    pos = pos + 1 -- opening quote
    local out = {}
    while true do
      if pos > #s then err("unterminated string") end
      local c = s:sub(pos, pos)
      if c == '"' then
        pos = pos + 1
        return table.concat(out)
      elseif c == "\\" then
        local e = s:sub(pos + 1, pos + 1)
        if e == "u" then
          local cp = tonumber(s:sub(pos + 2, pos + 5), 16)
          if not cp then err("bad \\u escape") end
          pos = pos + 6
          if cp >= 0xD800 and cp <= 0xDBFF and s:sub(pos, pos + 1) == "\\u" then
            local lo = tonumber(s:sub(pos + 2, pos + 5), 16)
            if lo and lo >= 0xDC00 and lo <= 0xDFFF then
              cp = 0x10000 + (cp - 0xD800) * 0x400 + (lo - 0xDC00)
              pos = pos + 6
            end
          end
          out[#out + 1] = u8(cp)
        else
          local map = { ['"'] = '"', ["\\"] = "\\", ["/"] = "/",
                        b = "\b", f = "\f", n = "\n", r = "\r", t = "\t" }
          local r = map[e]
          if not r then err("bad escape") end
          out[#out + 1] = r
          pos = pos + 2
        end
      else
        if s:byte(pos) < 0x20 then err("control char in string") end
        out[#out + 1] = c
        pos = pos + 1
      end
    end
  end
  local function parse_number()
    local head = s:match("^-?%d+%.?%d*", pos)
    if not head then err("bad value") end
    local tail = s:match("^[eE][+-]?%d+", pos + #head) or ""
    local raw = head .. tail
    if raw:match("[%.eE+-]$") then err("bad number") end
    pos = pos + #raw
    local n = tonumber(raw)
    if n == nil then err("bad number") end
    return n
  end
  local function parse_array()
    pos = pos + 1
    local t = json.array()
    skip()
    if s:sub(pos, pos) == "]" then pos = pos + 1; return t end
    while true do
      t[#t + 1] = parse_value()
      skip()
      local c = s:sub(pos, pos)
      if c == "]" then pos = pos + 1; return t end
      if c ~= "," then err("expected , or ]") end
      pos = pos + 1
      skip()
    end
  end
  local function parse_object()
    pos = pos + 1
    local t = {}
    skip()
    if s:sub(pos, pos) == "}" then pos = pos + 1; return t end
    while true do
      skip()
      if s:sub(pos, pos) ~= '"' then err("expected string key") end
      local k = parse_string()
      skip()
      if s:sub(pos, pos) ~= ":" then err("expected :") end
      pos = pos + 1
      skip()
      t[k] = parse_value()
      skip()
      local c = s:sub(pos, pos)
      if c == "}" then pos = pos + 1; return t end
      if c ~= "," then err("expected , or }") end
      pos = pos + 1
    end
  end
  parse_value = function()
    skip()
    local c = s:sub(pos, pos)
    if c == "{" then return parse_object() end
    if c == "[" then return parse_array() end
    if c == '"' then return parse_string() end
    if c == "t" and s:sub(pos, pos + 3) == "true" then pos = pos + 4; return true end
    if c == "f" and s:sub(pos, pos + 4) == "false" then pos = pos + 5; return false end
    if c == "n" and s:sub(pos, pos + 3) == "null" then pos = pos + 4; return json.null end
    if c == "-" or c:match("%d") then return parse_number() end
    err("bad value")
  end
  skip()
  local v = parse_value()
  skip()
  if pos <= #s then err("trailing characters") end
  return v
end

-- Shortest-roundtrip float emission (matches Python repr / serde_json over
-- the game domain; verified live by tests/test_lua_content.py). Tries
-- increasing precision and keeps the first form that round-trips, using
-- fixed notation exactly where Python does ([1e-4, 1e16)).
local function numstr(x)
  if x ~= x or x == math.huge or x == -math.huge then
    error("non-finite number")
  end
  if x == 0 then
    if 1 / x > 0 then return "0.0" else return "-0.0" end
  end
  if x % 1 == 0 and math.abs(x) < 1e15 then
    return string.format("%.0f", x)
  end
  local ae = math.abs(x)
  local sci = ae < 1e-4 or ae >= 1e16
  for p = 1, 17 do
    local s
    if sci then
      s = string.format("%." .. (p - 1) .. "e", x)
    else
      s = string.format("%." .. p .. "g", x)
    end
    if tonumber(s) == x then return s end
  end
  error("cannot round-trip float")
end

local function esc(s)
  return (s:gsub('[%z\1-\31\\"]', function(c)
    if c == '"' then return '\\"'
    elseif c == "\\" then return "\\\\"
    elseif c == "\n" then return "\\n"
    elseif c == "\r" then return "\\r"
    elseif c == "\t" then return "\\t"
    elseif c == "\b" then return "\\b"
    elseif c == "\f" then return "\\f"
    else return string.format("\\u%04x", c:byte()) end
  end))
end

local function enc(v)
  local tv = type(v)
  if tv == "string" then return '"' .. esc(v) .. '"' end
  if tv == "number" then return numstr(v) end
  if tv == "boolean" then return v and "true" or "false" end
  if tv == "table" then
    if v == json.null then return "null" end
    if json.is_array(v) then
      local parts = {}
      for i = 1, #v do parts[#parts + 1] = enc(v[i]) end
      return "[" .. table.concat(parts, ",") .. "]"
    end
    local keys = {}
    for k in pairs(v) do
      if type(k) ~= "string" then error("non-string object key") end
      keys[#keys + 1] = k
    end
    if #keys == 0 then error("ambiguous empty table (use json.array)") end
    table.sort(keys)
    local parts = {}
    for _, k in ipairs(keys) do
      parts[#parts + 1] = '"' .. esc(k) .. '":' .. enc(v[k])
    end
    return "{" .. table.concat(parts, ",") .. "}"
  end
  error("cannot encode " .. tv)
end

function json.encode(v) return enc(v) end

return json
