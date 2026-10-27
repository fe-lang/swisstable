# swisstable

A generic, growable SwissTable-style hash table written in Fe, extracted
from [fevm](https://github.com/fe-lang/fevm) with its library history intact.

`SwissTable<K, V>` stores entries in memory it owns, which it frees when it is
destroyed. Keys implement `SwissKey`, `Default`, and `Copy`; values implement
`Default` and `Copy`. The public API includes `empty`, `len`, `capacity`,
`is_empty`, `get`, `contains`, `insert`, `try_insert`, `try_reserve`, `remove`,
and `entry`. `get` returns a `Lookup<V>` with `found` and `value` fields.
`entry(slot)` reads one physical slot below `capacity()`, so callers can visit
every live entry; deleted and empty slots report `occupied: false`. Inserting an
existing key updates its value.

Slots come in groups of 16, a power of two of them; an empty table has none. A
key's search starts at the group its hash selects and reads slots in order until
an empty one. Entries and tombstones never fill more than 7/8 of the slots: an
insertion past that moves the entries to fresh slots, doubling them unless the
entries would fill at most half, and drops every tombstone. `insert` reverts with
`Panic(0x41)` when the table cannot allocate; `try_insert` and `try_reserve`
return `false` and leave the table as it was. Removing a key whose next slot is
empty leaves an empty slot, as do the tombstones before it, and removing the
last entry empties every slot.

The built-in `u256` key hash multiplies pairs of the key's 64-bit limbs,
offset by constants, into 128-bit products and folds each product's halves
together, as foldhash does. Custom keys must give equal keys equal hashes. The
group index comes from the hash's low bits and the seven-bit fingerprint from
its top bits. The deterministic hash does not provide hash-flood protection.

Add an immutable git revision to your ingot's `fe.toml`:

```toml
[dependencies]
swisstable = { source = "https://github.com/fe-lang/swisstable", rev = "<full commit SHA>" }
```

```fe
use swisstable::SwissTable

var table = SwissTable<u256, u256>::empty()
table.insert(17, 99)
let lookup = table.get(17)
core::assert(lookup.found && lookup.value == 99)
```

Use a Fe compiler with native backend support and owned-value destruction. All
eight library tests pass at O0/O1/O2 natively and on EVM on Linux x86_64 with
Fe `999ff9562` (branch `feat/owned-value-destruction`):

```sh
fe test --backend native -O 0 .
fe test --backend native -O 1 .
fe test --backend native -O 2 .
fe test .
```

The [native suite](native/README.md) owns dictionary-oracle checks, probe counts,
and benchmarks against the historical fixed-capacity baseline. It also runs the
library tests at each requested optimization level:

```sh
python3 native/run.py --fe /path/to/fe --out /tmp/swisstable-check --check-only
```

Use a fresh output directory. Correctness checks run at O0/O1/O2 by default;
omit `--check-only` to run lookup timing trials. The historical baseline is
preserved in this repository's git history, so a full clone is required.
