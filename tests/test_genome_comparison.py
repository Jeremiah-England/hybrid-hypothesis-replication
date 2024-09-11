import numpy as np
import pytest

from genome_comparison import (
    _encode_genome,
    compare_chunk,
    encode_base,
    find_matches,
    read_and_encode_genome,
)


def test_encode_base():
    assert encode_base(ord("A")) == 0
    assert encode_base(ord("a")) == 0
    assert encode_base(ord("C")) == 1
    assert encode_base(ord("c")) == 1
    assert encode_base(ord("G")) == 2
    assert encode_base(ord("g")) == 2
    assert encode_base(ord("T")) == 3
    assert encode_base(ord("t")) == 3
    assert encode_base(ord("N")) == -1


def test_encode_genome():
    input_genome = np.array([ord(c) for c in "ACGTACGTN"])
    expected_output = np.array([0, 1, 2, 3, 0, 1, 2, 3])
    np.testing.assert_array_equal(_encode_genome(input_genome), expected_output)


def test_read_and_encode_genome(tmp_path):
    # Create a temporary FASTA file
    fasta_content = ">test_genome\nACGTACGTN\nACGTACGT"
    fasta_file = tmp_path / "test_genome.fasta"
    fasta_file.write_text(fasta_content)

    expected_output = np.array([0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3, 0, 1, 2, 3])
    np.testing.assert_array_equal(read_and_encode_genome(str(fasta_file)), expected_output)


def test_compare_chunk():
    chunk = np.array([0, 1, 2, 3])
    target_genome = np.array([3, 2, 1, 0, 1, 2, 3, 0])

    assert compare_chunk(chunk, target_genome, max_differences=0)
    assert compare_chunk(chunk, target_genome, max_differences=1)
    assert compare_chunk(np.array([0, 0, 0, 0]), target_genome, max_differences=3)
    assert compare_chunk(np.array([1, 1, 1, 1]), target_genome, max_differences=2)
    assert not compare_chunk(np.array([1, 1, 1, 1]), target_genome, max_differences=1)


def test_find_matches():
    query_genome = np.array([0, 1, 1, 1, 0, 1, 2, 3])
    target_genome = np.array([3, 2, 1, 0, 1, 2, 3, 0])

    matching_chunks, total_chunks = find_matches(query_genome, target_genome, chunk_size=4, max_differences=1)
    assert matching_chunks == 3
    assert total_chunks == 5

    matching_chunks, total_chunks = find_matches(query_genome, target_genome, chunk_size=4, max_differences=0)
    assert matching_chunks == 2
    assert total_chunks == 5


if __name__ == "__main__":
    pytest.main([__file__])
