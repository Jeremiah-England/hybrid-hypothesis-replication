import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import polars as pl
from Levenshtein import distance
from tqdm import tqdm


@dataclass(frozen=True)
class GenomeChunk:
    species: str
    start_position: int
    sequence: str


def read_genome(file_path: Path) -> str:
    """Read a genome from a FASTA file."""
    with file_path.open("r") as f:
        return "".join(line.strip() for line in f if not line.startswith(">"))


def chunk_genome(genome: str, chunk_size: int = 40, step: int = 1) -> Iterable[tuple[int, str]]:
    """Generate chunks of the genome with a sliding window."""
    return ((i, genome[i : i + chunk_size]) for i in range(0, len(genome) - chunk_size + 1, step))


def find_match(query_chunk: GenomeChunk, target_genome: str, max_differences: int = 5) -> tuple[int, int] | None:
    """Find a match for a single query chunk in the target genome."""
    for i, target_seq in chunk_genome(target_genome):
        diff = distance(query_chunk.sequence, target_seq)
        if diff <= max_differences:
            return i, diff
    return None


def find_matches(
    query_chunks: Iterable[GenomeChunk],
    target_genome: str,
    max_differences: int = 5,
    chunk_count: int = 0,
) -> list[tuple[GenomeChunk, int, int]]:
    """Find matches for query chunks in the target genome."""
    matches: list[tuple[GenomeChunk, int, int]] = []

    start_time = perf_counter()
    progress_bar = tqdm(total=chunk_count * len(target_genome), desc="Processing comparisons", unit="comparison")

    for chunk in query_chunks:
        match = find_match(chunk, target_genome, max_differences)
        if match:
            matches.append((chunk, match[0], match[1]))
        progress_bar.update(len(target_genome))

    progress_bar.close()
    end_time = perf_counter()
    elapsed_time = end_time - start_time

    print(f"Total comparisons: {chunk_count}")
    print(f"Actual time taken: {elapsed_time:.2f} seconds")
    print(f"Average time per comparison: {(elapsed_time / chunk_count) * 1e6:.2f} microseconds")

    return matches


def compare_genomes(  # noqa: PLR0913
    species1: str, genome1: str, species2: str, genome2: str, chunk_size: int = 40, max_differences: int = 5
) -> pl.DataFrame:
    """Compare two genomes and return matches as a Polars DataFrame."""
    chunks1 = (
        GenomeChunk(species=species1, start_position=start, sequence=seq)
        for start, seq in chunk_genome(genome1, chunk_size)
    )
    matches = find_matches(chunks1, genome2, max_differences, chunk_count=len(genome1) // chunk_size + 1)

    return pl.DataFrame(
        {
            "query_species": [m[0].species for m in matches],
            "query_start": [m[0].start_position for m in matches],
            "query_sequence": [m[0].sequence for m in matches],
            "target_species": [species2] * len(matches),
            "target_start": [m[1] for m in matches],
            "differences": [m[2] for m in matches],
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

    genome1 = read_genome(Path(args.genome1))
    print(f"Read genome1: {args.genome1}")
    genome2 = read_genome(Path(args.genome2))
    print(f"Read genome2: {args.genome2}")

    result = compare_genomes(
        args.species1, genome1, args.species2, genome2, chunk_size=args.chunk_size, max_differences=args.max_differences
    )

    result.write_csv(args.output)
    print(f"Genome comparison completed. Results saved to {args.output}")


if __name__ == "__main__":
    main()
