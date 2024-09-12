from pathlib import Path

import numpy as np
import numpy.typing as npt
from numba import njit

# Constants for 2-bit encoding
A, C, G, T = 0, 1, 2, 3


@njit(nogil=True, nopython=True)
def encode_base(base: int) -> int:
    if base == 65 or base == 97:  # 'A' or 'a'
        return A
    elif base == 67 or base == 99:  # 'C' or 'c'
        return C
    elif base == 71 or base == 103:  # 'G' or 'g'
        return G
    elif base == 84 or base == 116:  # 'T' or 't'
        return T
    return -1  # For 'N' or any other character


def read_and_encode_genome(file_path: str) -> npt.NDArray[np.int8]:
    """Read a genome from a FASTA file and encode it as a 2-bit representation."""
    with Path(file_path).open("rb") as f:
        genome = b"".join(line.strip() for line in f if not line.startswith(b">"))

    encoded = np.frombuffer(genome, dtype=np.int8)
    return _encode_genome(encoded)


@njit(nogil=True, nopython=True)
def _encode_genome(genome: npt.NDArray[np.int8]) -> npt.NDArray[np.int8]:
    encoded = np.empty(genome.shape, dtype=np.int8)
    for i in range(len(genome)):
        encoded[i] = encode_base(genome[i])
    return encoded[encoded != -1]


@njit(nogil=True, nopython=True)
def compare_chunk(chunk: npt.NDArray[np.int8], target_genome: npt.NDArray[np.int8], max_differences: int) -> bool:
    """Check if the chunk matches anywhere in the target genome using bitwise XOR."""
    chunk_size = len(chunk)
    for i in range(len(target_genome) - chunk_size + 1):
        differences = np.sum(chunk != target_genome[i : i + chunk_size])
        if differences <= max_differences:
            return True
    return False


@njit(nogil=True, nopython=True)
def find_matches(
    query_genome: npt.NDArray[np.int8], target_genome: npt.NDArray[np.int8], chunk_size: int, max_differences: int
) -> tuple[int, int]:
    """Find matching chunks between query and target genomes."""
    total_chunks = len(query_genome) - chunk_size + 1
    matching_chunks = 0

    for i in range(total_chunks):
        chunk = query_genome[i : i + chunk_size]
        if compare_chunk(chunk, target_genome, max_differences):
            matching_chunks += 1

    return matching_chunks, total_chunks
