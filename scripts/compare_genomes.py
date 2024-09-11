import argparse
from pathlib import Path
from time import perf_counter

import numpy as np
import polars as pl
from tqdm import tqdm

from genome_comparison import read_and_encode_genome, find_matches


def compare_genomes(
    species1: str,
    genome1: np.ndarray,
    species2: str,
    genome2: np.ndarray,
    chunk_size: int = 40,
    max_differences: int = 5,
) -> pl.DataFrame:
    """Compare two genomes and return matches as a Polars DataFrame."""
    matching_chunks, total_chunks = find_matches(genome1, genome2, chunk_size, max_differences)

    return pl.DataFrame(
        {
            "query_species": [species1],
            "target_species": [species2],
            "matching_chunks": [matching_chunks],
            "total_chunks": [total_chunks],
            "similarity_percentage": [(matching_chunks / total_chunks) * 100],
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two genomes and find matches.")
    parser.add_argument("genome1", type=str, help="Path to the first genome file")
    parser.add_argument("species1", type=str, help="Name of the first species")
    parser.add_argument("genome2", type=str, help="Path to the second genome file")
    parser.add_argument("species2", type=str, help="Name of the second species")
    parser.add_argument("--chunk-size", type=int, default=40, help="Size of genome chunks (default: 40)")
    parser.add_argument("--max-differences", type=int, default=5, help="Maximum allowed differences (default: 5)")
    parser.add_argument(
        "--output", type=str, default="genome_comparison.csv", help="Output file name (default: genome_comparison.csv)"
    )

    args = parser.parse_args()

    start_time = perf_counter()

    print(f"Reading and encoding genome1: {args.genome1}")
    genome1 = read_and_encode_genome(args.genome1)
    print(f"Reading and encoding genome2: {args.genome2}")
    genome2 = read_and_encode_genome(args.genome2)

    print("Comparing genomes...")
    result = compare_genomes(
        args.species1, genome1, args.species2, genome2, chunk_size=args.chunk_size, max_differences=args.max_differences
    )

    end_time = perf_counter()
    elapsed_time = end_time - start_time

    print(f"Genome comparison completed in {elapsed_time:.2f} seconds.")
    print(f"Results:\n{result}")

    result.write_csv(args.output)
    print(f"Results saved to {args.output}")


if __name__ == "__main__":
    main()
