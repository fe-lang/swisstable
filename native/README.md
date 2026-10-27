# SwissTable hashing and probes

`hash_u256` multiplies the key's 64-bit limbs in pairs, each XORed with a
constant, into 128-bit products and folds each product's high and low words
together, as [foldhash][foldhash] does; a third folded multiply combines the
two lanes. `SwissKey.hash` returns `u64`. Equal keys must hash equally, and a
custom implementation should mix all key bits. The table selects its initial
16-slot group from the hash's low bits, as many as its capacity needs, and its
seven-bit fingerprint from the top seven bits. Equality resolves fingerprint
collisions.

The previous mixer multiplied a whole `u256` and shifted by small amounts. High
limbs did not reach the bits consumed by the table: varying limb 2 or 3 produced
identical initial groups and fingerprints. Narrowing before mixing would discard
those limbs; the new hash consumes all four limbs before its final multiply.

This deterministic, non-cryptographic hash does not provide hash-flood protection,
which production state storage still needs an explicit threat model for. The
table grows before entries and tombstones fill 7/8 of its slots, rehashing them
and dropping every tombstone; removal frees slots whose successor is empty, so a
miss stops at an empty slot however many entries were removed.

[foldhash]: https://github.com/orlp/foldhash

## Reproduce

Use a native-capable Fe compiler (see the repository README). Install Python
3.10+, Git, a C compiler, and binutils on x86_64 Linux, or Xcode command-line
tools on AArch64 macOS. No third-party Python packages are required. The baseline Git object must be
available locally (default `60017e7f2f033e971bdb2a5f5d4af097115f3be8`).
This MVS baseline preserves the historical `ab4cf7df` hash and table algorithms;
its only source changes are eleven mutable binding spellings. Both comparison
variants now use MVS syntax.

```sh
python3 native/run.py --fe /path/to/pinned/fe \
  --out /tmp/swisstable-check --check-only
python3 native/run.py --fe /path/to/pinned/fe \
  --out /tmp/swisstable-timing --levels 2
```

Use a fresh output directory. The first command checks O0/O1/O2. The second runs
alternating baseline/candidate timing trials at O2; it still checks every scenario
before measuring. Baseline and candidate table sources, generated executables,
objects, IR, assembly, the complete input corpus, host/compiler identities, hashes,
build/relink times, and code sizes are retained. Build times include report emission
and linking, and are single diagnostic observations. Text size includes the driver.

The runner first runs every library ingot test at each requested optimization
level, then generates standalone roots from exact table source snapshots. The
candidate is this checkout's `src/lib.fe`; its source hash and repository state
are recorded. The generated roots give the diagnostic executable access to private table fields
without adding counters or diagnostic methods to the production API.

## What is checked and measured

- Six key families: sequential values in each of the four limbs, repeated limbs,
  and deterministic random full-width keys.
- Occupancies of 64, 128, 224, and 256 entries. Each is tested fresh, after three
  complete replacement cycles, and after filling to 256 entries and deleting down
  to the requested occupancy. Hits and misses are measured separately.
- Dictionary-oracle traces include existing-key updates, unsuccessful removals,
  2,048 mixed operations and, for the fixed 256-slot baseline, capacity failures.
  Runtime hash checks cover every single bit, complemented bit, adjacent pair,
  and random full-width keys.
- Separate diagnostic builds count actual visited groups, inspected control
  bytes, and equality checks for every operation and query. Every count is
  compared with an independent physical model of each variant: the baseline's
  256 fixed slots and the candidate's growth, rehashing and slot reclamation.
  Histograms, means, p95, maxima, and retained tombstone counts are recorded.

Timed executables have no probe instrumentation. Runtime keys and values arrive
through stdin; setup, individual correctness queries, and output are outside the
CPU clock interval. Each lookup result influences the next query index, and a
checksum covers the returned values and presence bits. Even-valued inputs make
the traversal visit every query in order; every batch checksum is checked.
Each process discards a warmup batch. Baseline/candidate order alternates across
trials, and all sample values are retained. These are hot-table lookup costs,
including hashing and loop overhead, not whole-EVM throughput or insertion timings.

Run on an idle machine: CPU clocks exclude descheduling, but frequency, thermal
state, and other workloads still affect results. Linux execution requires a Linux
runner; a macOS result does not establish cross-platform acceptance.


The runner passes all 2,004 scenario checks across its 12 O0/O1/O2 builds (both
variants, with and without probe instrumentation), including dictionary behavior
and the physical probe counts of both models. All eight library tests also pass at
every level. This check used Fe `71ffd7ca4` (branch `feat/generic-byte-order`)
on x86_64 Linux; timing trials were omitted.
