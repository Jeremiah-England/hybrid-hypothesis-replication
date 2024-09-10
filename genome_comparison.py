from pathlib import Path

from Levenshtein import distance


def read_genome(file_path: str) -> str:
    """Read a genome from a FASTA file."""
    with Path(file_path).open("r") as f:
        return "".join(line.strip() for line in f if not line.startswith(">"))


def compare_chunk(chunk: str, target_genome: str, max_differences: int) -> bool:
    """Check if the chunk matches anywhere in the target genome."""
    chunk_size = len(chunk)
    for i in range(len(target_genome) - chunk_size + 1):
        if distance(chunk, target_genome[i : i + chunk_size]) <= max_differences:
            return True
    return False
