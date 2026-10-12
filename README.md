# swisstable

A generic, fixed-capacity SwissTable-style hash table written in Fe, extracted
from [fevm](https://github.com/fe-lang/fevm) with its library history intact.

`SwissTable<K, V>` stores up to 256 entries. Keys implement `SwissKey`, `Default`,
and `Copy`; values implement `Default` and `Copy`. The public API includes
`empty`, `len`, `capacity`, `is_empty`, `get`, `contains`, `insert`, and `remove`.
`get` returns a `Lookup<V>` with `found` and `value` fields. Inserting an existing
key updates its value; inserting a new key into a full table returns `false`.

The built-in `u256` key hash is XXH64 with seed zero over the key's 32
little-endian bytes. Custom keys must give equal keys equal hashes.
The table uses scalar probing, retains tombstones, and has no growth or tombstone
cleanup policy. Its deterministic hash does not provide hash-flood protection.

Add an immutable git revision to your ingot's `fe.toml`:

```toml
[dependencies]
swisstable = { source = "https://github.com/fe-lang/swisstable", rev = "<full commit SHA>" }
```

```fe
use swisstable::SwissTable

var table = SwissTable<u256, u256>::empty()
core::assert(table.insert(17, 99))
let lookup = table.get(17)
core::assert(lookup.found && lookup.value == 99)
```

Use a Fe compiler with native backend support. The extraction was verified with
Fe `09aed1e8817d0be5a9340dc7d6ad3fd7fec43f50`, the compiler pinned by fevm at
extraction time. Run all six library tests at each optimization level:

```sh
fe test --backend native -O 0 .
fe test --backend native -O 1 .
fe test --backend native -O 2 .
```

The [native suite](native/README.md) owns dictionary-oracle checks, probe counts,
and baseline/candidate benchmarks. It also runs the six library tests at each
requested optimization level:

```sh
python3 native/run.py --fe /path/to/pinned/fe --out /tmp/swisstable-check --check-only
```

Use a fresh output directory. Correctness checks run at O0/O1/O2 by default;
omit `--check-only` to run lookup timing trials. The historical baseline is
preserved in this repository's git history, so a full clone is required.

The MVS port passes all six library tests at O0/O1/O2 on Linux x86_64 with
`sbillig/fe:mvs` at `fe5c32c1b9913a259667be9123a9090beb16ed1a` and native support.
Mutable values and generated native drivers use `var` bindings.
