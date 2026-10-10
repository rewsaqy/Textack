# textack-sim (Rust)

Sim worker in Rust: protocol v1 over stdio, bit-identical to Python.

## Build

```bash
cargo build --manifest-path rs/textack-sim/Cargo.toml
# binary: rs/textack-sim/target/debug/textack-sim
```

Needs a Rust toolchain (`rustup`), plus `serde`/`serde_json` from
crates.io on first build (`Cargo.lock` is committed for reproducibility).
No toolchain needed to *play*: the classic Python path is the default.

## Run

```bash
echo '{"v":1,"t":"ping","id":1}' | ./rs/textack-sim/target/debug/textack-sim
# {"t":"pong","id":1,"v":1}
```

## Prove it

```bash
cargo test --manifest-path rs/textack-sim/Cargo.toml   # MT vectors
python -m pytest tests/test_rust_sim.py -q              # cross-language
```

The cross-language battery compares ~1000 seeded replies against
`Sim.handle` live — any drift fails loudly. The MT19937 core replicates
CPython's `random` bit-exact (seeding, `random()`, `getrandbits`,
`randbelow`, `shuffle`, `choice`); see `src/mt.rs` and the "Deterministic
RNG" section of `docs/PROTOCOL.md`.
