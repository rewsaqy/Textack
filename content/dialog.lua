-- Operator dialog (mirrors textack/core/story.py; strings verbatim).
-- Cross-checked line-by-line by tests/test_lua_content.py.
return {
  order = { "aika", "rin", "sora" },
  unlock_wave = { aika = 1, rin = 4, sora = 8 },
  waifus = {
    aika = {
      name = "AIKA",
      idle = {
        "Type fast = big damage, senpai!",
        "PERFECT hits land inside the gold window.",
        "Combo is just crit with extra steps!",
      },
      wave = {
        "Wave {wave}! {enemy} incoming — type fast, senpai!",
        "{enemy} spotted at wave {wave}. Eyes on the keys!",
        "Wave {wave} — show this {enemy} what we're made of!",
        "Here comes wave {wave}! Don't blink, don't typo!",
        "{enemy} at wave {wave}. I believe in your fingers!",
        "Wave {wave}, let's go! Speed is our armor!",
      },
      boss = {
        "BOSS at wave {wave}! This {enemy} is huge — focus!",
        "Wave {wave} boss: {enemy}. Deep breath. Perfect aim!",
        "Careful, senpai — {enemy} hits like a truck!",
      },
      clear = {
        "Wave clear! Sugoi, senpai!",
        "Did you see that explosion? Nice shot!",
        "Enemy fortress dented. Onward!",
      },
      defeat = {
        "Our fortress... don't cry, we'll rebuild!",
        "It's okay, senpai. One more run?",
      },
      happy = { "Sugoi! Direct hit!", "Nice shot, senpai!", "Combo rising!" },
      sad = { "Baka... that was a miss!", "Focus, senpai!", "Combo reset..." },
      hurt = { "Itai! Protect the base!", "Our fortress is burning!", "Kyaa!" },
      excited = { "Level up! We're getting stronger!", "Power rising!", "Yosha!" },
    },
    rin = {
      name = "RIN",
      idle = {
        "Slow is smooth. Smooth is fast.",
        "One word. One bullet.",
        "Accuracy first. Speed follows.",
      },
      wave = {
        "Wave {wave}. {enemy} on scope. Breathe. Type.",
        "{enemy} at wave {wave}. Wind calm. Fire.",
        "Wave {wave}. I count six typos before breakfast. Make none.",
        "Target: {enemy}. Wave {wave}. Execute.",
        "Wave {wave} — patience, hunter. Then strike.",
        "{enemy} approaches. Wave {wave}. Steady...",
      },
      boss = {
        "Boss. {enemy}, wave {wave}. One shot, one kill.",
        "Wave {wave}: {enemy}. Aim for the weak syllable.",
        "Big target. Can't miss. ...Don't miss.",
      },
      clear = {
        "Target neutralized. Next.",
        "Clean shot. As expected.",
        "Wave clear. Reloading fingers.",
      },
      defeat = {
        "Missed the vital point... again soon.",
        "Retreat is also a tactic. Regroup.",
      },
      happy = { "Bullseye.", "Clean hit.", "As calculated." },
      sad = { "Tch. Missed.", "Recalibrating.", "Wind... my fault." },
      hurt = { "Guh—! Base armor failing!", "Damage report, now!",
               "They found our range!" },
      excited = { "New scope acquired. Stronger.", "Upgraded. Lethal.",
                  "Hm. Not bad." },
      unlock_line = "RIN here. Wave {wave} reached — I'll cover your typos. Don't waste my bullets.",
    },
    sora = {
      name = "SORA",
      idle = {
        "I tuned the turret! It shoots by itself now!",
        "Did you know? Typing burns calories. Probably.",
        "Wrench + keyboard = victory!",
      },
      wave = {
        "Ooh, wave {wave}! Let's dismantle this {enemy}!",
        "{enemy}? At wave {wave}? My turret's been waiting!",
        "Wave {wave}! I oiled the keys for maximum speed!",
        "Behold, wave {wave}! Science vs {enemy} — science wins!",
        "Wave {wave} incoming! Hold my wrench!",
        "{enemy} at wave {wave}. Time for field testing!",
      },
      boss = {
        "WHOA, big {enemy} at wave {wave}! My favorite kind!",
        "Boss wave {wave}! Let me overclock... the keyboard!",
        "{enemy}?! Finally, a worthy experiment!",
      },
      clear = {
        "BOOM! Did you see that?!",
        "Experiment: success! Hypothesis: we're awesome!",
        "Wave clear! Turret high-five!",
      },
      defeat = {
        "The base... my beautiful base... rebuild! Improve!",
        "Test failed! Adjust variables! Retry!",
      },
      happy = { "Eureka! Hit!", "Science prevails!", "Woohoo!" },
      sad = { "Oopsie... misfire!", "Bug in the system! Your fingers!",
              "Recalibrate the human!" },
      hurt = { "My turret!! Our base!!", "Hull breach! Grab a wrench!",
               "Eeeek!" },
      excited = { "UPGRADE! *excited wrench noises*",
                  "New gadget installed!", "Power output doubled! Ish!" },
      unlock_line = "SORA reporting! You hit wave {wave} — that deserves automated firepower! Turret online!",
    },
  },
}
