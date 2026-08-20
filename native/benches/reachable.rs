//! Packed bitplanes vs. one byte per sum, at the shapes this engine actually
//! sees. Sizes come from the seed-20260821 portfolio (see `native/BENCH.md`):
//! rung-0 pools are p50 ~185 / p90 ~430 orders, and credits run to a few lakh
//! rupees, so `target` is in the 10^5..10^6 paise band.
//!
//! The `python` feature is off here on purpose -- linking libpython would put
//! interpreter noise into a measurement whose whole point is cache behaviour.

use attest_native::reachable::{reachable, reachable_u8};
use criterion::{criterion_group, criterion_main, BenchmarkId, Criterion, Throughput};

/// Deterministic nets, drawn to look like order values: a few hundred rupees to
/// a few thousand, in paise, with no structure the DP could exploit.
fn nets(n: usize, seed: u64) -> Vec<u64> {
    let mut s = seed | 1;
    (0..n)
        .map(|_| {
            s ^= s << 13;
            s ^= s >> 7;
            s ^= s << 17;
            20_000 + s % 480_000
        })
        .collect()
}

/// (pool size, target paise). Chosen to sweep the crossover rather than to
/// flatter either implementation.
const SHAPES: &[(usize, u64)] = &[
    (8, 50_000),
    (32, 200_000),
    (64, 500_000),
    (185, 500_000),   // p50 pool, mid credit
    (185, 1_500_000),
    (430, 1_500_000), // p90 pool
    (430, 3_000_000), // p90 pool at MAX_TARGET_PAISE
    (900, 3_000_000), // MAX_POOL at MAX_TARGET_PAISE -- the production ceiling
];

fn bench(c: &mut Criterion) {
    let mut g = c.benchmark_group("reachable");
    for &(n, target) in SHAPES {
        let v = nets(n, 0x2026_0821 ^ n as u64);
        // Cell updates, so ns/iter converts directly to ns per DP cell and the
        // two implementations are comparable across shapes.
        g.throughput(Throughput::Elements(n as u64 * (target + 1)));
        let id = format!("n{n}_t{target}");
        g.bench_with_input(BenchmarkId::new("packed2bit", &id), &v, |b, v| {
            b.iter(|| reachable(std::hint::black_box(v), target))
        });
        g.bench_with_input(BenchmarkId::new("bytes", &id), &v, |b, v| {
            b.iter(|| reachable_u8(std::hint::black_box(v), target))
        });
    }
    g.finish();
}

criterion_group!(benches, bench);
criterion_main!(benches);
