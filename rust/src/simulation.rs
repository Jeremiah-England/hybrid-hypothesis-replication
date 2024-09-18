use crate::genome_comparison::GenomeComparison;
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use rand::Rng;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationState {
    pub human_only: usize,
    pub human_genome1: usize,
    pub human_genome2: usize,
    pub human_genome3: usize,
    pub human_genome1_genome2: usize,
    pub human_genome1_genome3: usize,
    pub human_genome2_genome3: usize,
    pub human_genome1_genome2_genome3: usize,
    pub total_comparisons: usize,
}

impl Default for SimulationState {
    fn default() -> Self {
        SimulationState {
            human_only: 0,
            human_genome1: 0,
            human_genome2: 0,
            human_genome3: 0,
            human_genome1_genome2: 0,
            human_genome1_genome3: 0,
            human_genome2_genome3: 0,
            human_genome1_genome2_genome3: 0,
            total_comparisons: 0,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationConfig {
    pub chunk_size: u32,
    pub max_differences: u32,
    pub num_processes: usize,
    pub update_interval: usize,
    pub human_genome_path: String,
    pub genome1_path: String,
    pub genome2_path: String,
    pub genome3_path: String,
    pub genome1_name: String,
    pub genome2_name: String,
    pub genome3_name: String,
}

pub struct Simulation {
    config: SimulationConfig,
    state: Arc<Mutex<SimulationState>>,
    genome1_comparison: GenomeComparison,
    genome2_comparison: GenomeComparison,
    genome3_comparison: Option<GenomeComparison>,
    // Remove this line: genome_comparison: Arc<Mutex<Option<GenomeComparison>>>,
}

impl Simulation {
    pub fn new(config: SimulationConfig) -> Self {
        let genome1_comparison = GenomeComparison::new(
            &config.human_genome_path,
            &config.genome1_path,
            config.chunk_size,
            config.max_differences,
        );
        let genome2_comparison = GenomeComparison::new(
            &config.human_genome_path,
            &config.genome2_path,
            config.chunk_size,
            config.max_differences,
        );
        let genome3_comparison = if !config.genome3_path.is_empty() {
            Some(GenomeComparison::new(
                &config.human_genome_path,
                &config.genome3_path,
                config.chunk_size,
                config.max_differences,
            ))
        } else {
            None
        };

        Simulation {
            config,
            state: Arc::new(Mutex::new(SimulationState::default())),
            genome1_comparison,
            genome2_comparison,
            genome3_comparison,
            // Remove this line: genome_comparison: Arc::new(Mutex::new(None)),
        }
    }

    pub fn run_comparison(&self) -> (bool, bool, bool) {
        let query_len = self.genome1_comparison.get_query_genome_len();
        let chunk_size = self.config.chunk_size;
        let max_start = query_len.saturating_sub(chunk_size as usize);
        let chunk_start = rand::thread_rng().gen_range(0..=max_start);
        
        (
            self.genome1_comparison.compare(chunk_start),
            self.genome2_comparison.compare(chunk_start),
            self.genome3_comparison.as_ref().map_or(false, |g| g.compare(chunk_start))
        )
    }

    pub fn update_state(&self, genome1_match: bool, genome2_match: bool, genome3_match: bool) {
        let mut state = self.state.lock().unwrap();
        match (genome1_match, genome2_match, genome3_match) {
            (true, true, true) => state.human_genome1_genome2_genome3 += 1,
            (true, true, false) => state.human_genome1_genome2 += 1,
            (true, false, true) => state.human_genome1_genome3 += 1,
            (false, true, true) => state.human_genome2_genome3 += 1,
            (true, false, false) => state.human_genome1 += 1,
            (false, true, false) => state.human_genome2 += 1,
            (false, false, true) => state.human_genome3 += 1,
            (false, false, false) => state.human_only += 1,
        }
        state.total_comparisons += 1;
    }

    pub fn run_simulation(&self, num_comparisons: usize) {
        for _ in 0..num_comparisons {
            let (genome1_match, genome2_match, genome3_match) = self.run_comparison();
            self.update_state(genome1_match, genome2_match, genome3_match);
        }
    }

    pub fn get_state(&self) -> SimulationState {
        self.state.lock().unwrap().clone()
    }

    pub fn get_config(&self) -> SimulationConfig {
        self.config.clone()
    }
}