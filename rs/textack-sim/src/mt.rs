//! MT19937 twin of CPython's `random` (Mersenne Twister, 53-bit `random()`).
//!
//! Seeding replicates `random.seed(int)` for non-negative ints: the key is
//! the minimal little-endian 32-bit words of the seed, fed through the
//! reference `init_by_array` after `init_genrand(19650218)`.
//! Higher-level helpers mirror CPython exactly: `random()` (53-bit),
//! `getrandbits` (top k bits), `randbelow` (rejection loop), Fisher-Yates
//! `shuffle` (descending), and `choice` (index via `_randbelow(len)`).
//! Proven by the vectors below (captured from CPython) and live by
//! tests/test_rust_sim.py.

const N: usize = 624;
const M: usize = 397;
const MATRIX_A: u32 = 0x9908b0df;
const UPPER_MASK: u32 = 0x80000000;
const LOWER_MASK: u32 = 0x7fffffff;

pub struct Mt {
    mt: [u32; N],
    index: usize,
}

impl Mt {
    fn init_genrand(&mut self, s: u32) {
        self.mt[0] = s;
        for i in 1..N {
            let p = self.mt[i - 1];
            self.mt[i] = 1812433253u32
                .wrapping_mul(p ^ (p >> 30))
                .wrapping_add(i as u32);
        }
        self.index = N;
    }

    pub fn from_words(key: &[u32]) -> Self {
        let mut m = Mt { mt: [0; N], index: N };
        m.init_genrand(19650218);
        let klen = key.len().max(1);
        let mut i = 1usize;
        let mut j = 0usize;
        for _ in 0..N.max(klen) {
            let p = m.mt[i - 1];
            let kw = if key.is_empty() { 0 } else { key[j] };
            m.mt[i] = (m.mt[i] ^ ((p ^ (p >> 30)).wrapping_mul(1664525)))
                .wrapping_add(kw)
                .wrapping_add(j as u32);
            i += 1;
            j += 1;
            if i >= N {
                m.mt[0] = m.mt[N - 1];
                i = 1;
            }
            if j >= klen {
                j = 0;
            }
        }
        for _ in 0..(N - 1) {
            let p = m.mt[i - 1];
            m.mt[i] = (m.mt[i] ^ ((p ^ (p >> 30)).wrapping_mul(1566083941)))
                .wrapping_sub(i as u32);
            i += 1;
            if i >= N {
                m.mt[0] = m.mt[N - 1];
                i = 1;
            }
        }
        m.mt[0] = 0x80000000;
        m.index = N;
        m
    }

    /// Non-negative seed → minimal little-endian 32-bit words.
    pub fn from_seed(seed: u64) -> Self {
        let mut words = Vec::new();
        let mut s = seed;
        loop {
            words.push((s & 0xffff_ffff) as u32);
            s >>= 32;
            if s == 0 {
                break;
            }
        }
        Self::from_words(&words)
    }

    pub fn u32(&mut self) -> u32 {
        if self.index >= N {
            self.twist();
        }
        let mut y = self.mt[self.index];
        self.index += 1;
        y ^= y >> 11;
        y ^= (y << 7) & 0x9d2c5680;
        y ^= (y << 15) & 0xefc60000;
        y ^= y >> 18;
        y
    }

    fn twist(&mut self) {
        for i in 0..N {
            let x = (self.mt[i] & UPPER_MASK) | (self.mt[(i + 1) % N] & LOWER_MASK);
            let mut xa = x >> 1;
            if x & 1 != 0 {
                xa ^= MATRIX_A;
            }
            self.mt[i] = self.mt[(i + M) % N] ^ xa;
        }
        self.index = 0;
    }

    pub fn random(&mut self) -> f64 {
        let a = (self.u32() >> 5) as f64;
        let b = (self.u32() >> 6) as f64;
        (a * 67108864.0 + b) / 9007199254740992.0
    }

    pub fn getrandbits(&mut self, k: u32) -> u64 {
        if k == 0 {
            return 0;
        }
        let words = (k - 1) / 32 + 1;
        let mut r: u64 = 0;
        for _ in 0..words {
            r = (r << 32) | self.u32() as u64;
        }
        r >> (words * 32 - k)
    }

    pub fn randbelow(&mut self, n: u64) -> u64 {
        assert!(n > 0);
        // NB: CPython uses n.bit_length(), NOT (n - 1): powers of two
        // need the full width (rejection does the rest).
        let k = 64 - n.leading_zeros();
        loop {
            let r = self.getrandbits(k);
            if r < n {
                return r;
            }
        }
    }

    pub fn shuffle<T>(&mut self, v: &mut [T]) {
        for i in (1..v.len()).rev() {
            let j = self.randbelow(i as u64 + 1) as usize;
            v.swap(i, j);
        }
    }

    /// CPython's `choice(seq)`: index via `_randbelow(len)`, NOT
    /// `floor(random() * n)` (uniformity fix upstream).
    pub fn choice_index(&mut self, n: usize) -> usize {
        self.randbelow(n as u64) as usize
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn u32seq(seed: u64) -> [u32; 3] {
        let mut m = Mt::from_seed(seed);
        [m.u32(), m.u32(), m.u32()]
    }

    fn f64seq(seed: u64) -> [f64; 3] {
        let mut m = Mt::from_seed(seed);
        [m.random(), m.random(), m.random()]
    }

    #[test]
    fn genrand_matches_cpython() {
        assert_eq!(u32seq(0), [3626764237, 1654615998, 3255389356]);
        assert_eq!(u32seq(1), [577090037, 2444712010, 3639700191]);
        assert_eq!(u32seq(7), [1390851128, 4071050724, 647892279]);
        assert_eq!(u32seq(42), [2746317213, 478163327, 107420369]);
        assert_eq!(u32seq(99), [1735072617, 1635320116, 859317502]);
        assert_eq!(u32seq(12345), [1789368711, 3146859322, 43676229]);
        assert_eq!(u32seq(2147483647), [1364760256, 4023463762, 3510513048]);
        assert_eq!(u32seq(4294967295), [2728839433, 2661025012, 872737089]);
        assert_eq!(u32seq(4294967296), [485306839, 1508871100, 1794561286]);
        // 2^64 + 12345 exceeds u64: explicit little-endian words [12345, 0, 1]
        let mut m = Mt::from_words(&[12345, 0, 1]);
        assert_eq!([m.u32(), m.u32(), m.u32()], [2632172, 2355889752, 3906953032]);
    }

    #[test]
    fn random_f64_matches_cpython() {
        assert_eq!(f64seq(0), [0.8444218515250481, 0.7579544029403025, 0.420571580830845]);
        assert_eq!(f64seq(1), [0.13436424411240122, 0.8474337369372327, 0.763774618976614]);
        assert_eq!(f64seq(7), [0.32383276483316237, 0.15084917392450192, 0.6509344730398537]);
        assert_eq!(f64seq(42), [0.6394267984578837, 0.025010755222666936, 0.27502931836911926]);
    }

    #[test]
    fn randbelow_shuffle_choice_match_cpython() {
        let mut m = Mt::from_seed(7);
        assert_eq!([m.randbelow(10), m.randbelow(10), m.randbelow(10)], [5, 2, 6]);
        let mut m = Mt::from_seed(42);
        let mut v: Vec<i32> = (0..10).collect();
        m.shuffle(&mut v);
        assert_eq!(v, vec![7, 3, 2, 8, 5, 6, 9, 4, 0, 1]);
        let mut m = Mt::from_seed(0);
        let abc = ["a", "b", "c", "d"];
        let got: Vec<&str> = (0..3).map(|_| abc[m.choice_index(4)]).collect();
        assert_eq!(got, vec!["d", "d", "a"]);
    }
}
