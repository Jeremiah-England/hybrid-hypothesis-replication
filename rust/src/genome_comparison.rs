// Start of Selection
use std::collections::HashMap;
use std::fs;
use serde::{Serialize, Deserialize};
use std::mem;

const A: u8 = 0;
const C: u8 = 1;
const G: u8 = 2;
const T: u8 = 3;
const N: u8 = 4;
const UNKNOWN: u8 = 5;

// Precomputed lookup table for faster base encoding
const ENCODE_TABLE: [u8; 256] = {
    let mut table = [UNKNOWN; 256];
    let mut i = 0;
    while i < 256 {
        table[i] = match i as u8 {
            b'A' | b'a' => A,
            b'C' | b'c' => C,
            b'G' | b'g' => G,
            b'T' | b't' => T,
            b'N' | b'n' => N,
            _ => UNKNOWN,
        };
        i += 1;
    }
    table
};

pub fn read_and_encode_genome(file_path: &str) -> Vec<u8> {
    let data = fs::read(file_path).expect("Failed to read genome file");
    let mut encoded = Vec::with_capacity(data.len());
    let mut skip = false;

    for &byte in &data {
        match byte {
            b'>' => {
                skip = true;
            }
            b'\n' => {
                skip = false;
            }
            b'\r' => {
                // Ignore carriage returns
            }
            _ => {
                if !skip {
                    let encoded_byte = ENCODE_TABLE[byte as usize];
                    if encoded_byte != UNKNOWN {
                        encoded.push(encoded_byte);
                    }
                }
            }
        }
    }

    encoded
}

const BASE_OPTIONS: usize = 5; // A, C, G, T, N

#[derive(Serialize, Deserialize)]
pub struct GenomeIndex {
    pub index: Vec<Vec<u32>>,
    pub part_size: u32,
}

impl GenomeIndex {
    pub fn new(genome: &[u8], part_size: u32, chunk_size: u32) -> Self {
        log::info!("Building index for genome of length {} with part size {} and chunk size {}", genome.len(), part_size, chunk_size);
        let index_size = BASE_OPTIONS.pow(part_size as u32);
        let mut index = vec![Vec::<u32>::new(); index_size];
        let safe_end = (genome.len() as u32) - chunk_size + 1;

        for i in 0..safe_end {
            if i % (safe_end / 100) == 0 {
                log::info!("Indexing at position {} ({}%)", i, (i as f64 / safe_end as f64) * 100.0);
            }
            let key = Self::hash(&genome[i as usize..i as usize + part_size as usize]);
            index[key].push(i);
        }

        GenomeIndex { index, part_size }
    }

    fn hash(key: &[u8]) -> usize {
        key.iter().fold(0, |acc, &base| acc * BASE_OPTIONS + base as usize)
    }

    pub fn get(&self, key: &[u8]) -> Option<&Vec<u32>> {
        let hash = Self::hash(key);
        self.index.get(hash).filter(|v| !v.is_empty())
    }
}

pub fn hamming_distance(a: &[u8], b: &[u8]) -> u32 {
    a.iter().zip(b).filter(|&(x, y)| x != y).count() as u32
}

pub fn find_matches(
    query_genome: &[u8],
    target_index: &GenomeIndex,
    target_genome: &[u8],
    chunk_size: u32,
    max_differences: u32,
) -> bool {
    let num_parts = max_differences + 1;
    let part_size = target_index.part_size;

    (0..num_parts).any(|j| {
        let part = &query_genome[j as usize * part_size as usize..(j + 1) as usize * part_size as usize];
        if let Some(positions) = target_index.get(part) {
            positions.iter().any(|&pos| {
                let start = pos.saturating_sub(j * part_size);
                let end = (start + chunk_size).min(target_genome.len() as u32);
                let target_chunk = &target_genome[start as usize..end as usize];
                target_chunk.len() == chunk_size as usize
                    && hamming_distance(query_genome, target_chunk) <= max_differences
            })
        } else {
            false
        }
    })
}

pub struct GenomeComparison {
    query_genome: Vec<u8>,
    target_genome: Vec<u8>,
    target_index: GenomeIndex,
    chunk_size: u32,
    max_differences: u32,
}

impl GenomeComparison {
    pub fn new(
        query_path: &str,
        target_path: &str,
        chunk_size: u32,
        max_differences: u32,
    ) -> Self {
        use std::fs;
        use std::path::Path;
        use bincode;

        fn get_cache_path(file_path: &str, suffix: &str) -> String {
            let path = Path::new(file_path);
            let file_stem = path.file_stem().unwrap().to_str().unwrap();
            let cache_dir = Path::new("cache");
            fs::create_dir_all(cache_dir).unwrap();
            cache_dir.join(format!("{}{}", file_stem, suffix)).to_str().unwrap().to_string()
        }

        let query_genome = {
            let cache_path = get_cache_path(query_path, "_genome.bin");
            if Path::new(&cache_path).exists() {
                log::info!("Loading cached genome for {}", query_path);
                bincode::deserialize(&fs::read(&cache_path).unwrap()).unwrap()
            } else {
                log::info!("Reading and encoding genome for {}", query_path);
                let genome = read_and_encode_genome(query_path);
                log::info!("Genome length: {}", genome.len());
                fs::write(&cache_path, bincode::serialize(&genome).unwrap()).unwrap();
                genome
            }
        };

        let target_genome = {
            let cache_path = get_cache_path(target_path, "_genome.bin");
            if Path::new(&cache_path).exists() {
                log::info!("Loading cached genome for {}", target_path);
                bincode::deserialize(&fs::read(&cache_path).unwrap()).unwrap()
            } else {
                log::info!("Reading and encoding genome for {}", target_path);
                let genome = read_and_encode_genome(target_path);
                log::info!("Genome length: {}", genome.len());
                fs::write(&cache_path, bincode::serialize(&genome).unwrap()).unwrap();
                genome
            }
        };

        let target_index = {
            let cache_path = get_cache_path(target_path, &format!("_index_{}_{}.bin", chunk_size, max_differences));
            if Path::new(&cache_path).exists() {
                log::info!("Loading cached index for {} and {}", query_path, target_path);
                bincode::deserialize(&fs::read(&cache_path).unwrap()).unwrap()
            } else {
                log::info!("Building index for {} and {}", query_path, target_path);
                let index = GenomeIndex::new(&target_genome, chunk_size / (max_differences + 1), chunk_size as u32);
                fs::write(&cache_path, bincode::serialize(&index).unwrap()).unwrap();
                log::info!("Index built and cached for {} and {}", query_path, target_path);
                index
            }
        };

        GenomeComparison {
            query_genome,
            target_genome,
            target_index,
            chunk_size,
            max_differences,
        }
    }

    pub fn compare(&self, chunk_start: usize) -> bool {
        let chunk = &self.query_genome[chunk_start..chunk_start + self.chunk_size as usize];
        find_matches(
            chunk,
            &self.target_index,
            &self.target_genome,
            self.chunk_size,
            self.max_differences,
        )
    }

    pub fn get_query_genome_len(&self) -> usize {
        self.query_genome.len()
    }
}