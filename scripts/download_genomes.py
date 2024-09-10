"""
Download genomes from the internet.

To download the bonobo, human, and pig genomes, you'll need to access genomic databases and use bioinformatics tools.
Here's a general guide on how to obtain these genomes:

Bonobo Genome:
The bonobo genome assembly is available from the Max Planck Institute for Evolutionary Anthropology. You can download it
as follows:
- Go to http://bioinf.eva.mpg.de/bonobo

    Index of /bonobo
    [ICO]	Name	Last modified	Size	Description
    [PARENTDIR]	Parent Directory
    [   ]	README	2012-05-04 18:01	789
    [   ]	chr.fa.gz	2012-05-04 13:00	803M
    [   ]	contigs.fa.gz	2012-05-04 13:01	735M
    [   ]	contigs.qual.gz	2012-05-04 13:01	39M
    [   ]	contigs_to_scaffolds.agp	2012-05-04 13:01	13M
    [DIR]	paper_data_sets/	2012-09-17 10:43
    [   ]	scaffolds.fa.gz	2012-05-04 13:02	801M
    [   ]	scaffolds_to_chr.agp	2012-05-04 13:02	1.1M
    Max Planck Institute for Evolutionary Anthropology |. Imprint |. Privacy Policy

- Download the contigs, scaffolds, and chromosome-assigned scaffolds in FASTA format
- Alternatively, access the scaffolds and contigs from GenBank (accession AJFE01000000)

Human Genome:
The human genome can be downloaded from several sources. A common resource is the UCSC Genome Browser:
- Visit https://hgdownload.soe.ucsc.edu/downloads.html
- Select the latest human genome assembly (e.g., GRCh38/hg38)
- Download the desired file formats (FASTA, etc.)

Pig Genome:
The pig genome can be obtained from the Ensembl database:
- Go to https://www.ensembl.org/Sus_scrofa/Info/Index
- Click on "Download DNA sequence (FASTA)"
- Select the desired assembly and download options

General Tips:
- Use command-line tools like wget or curl to download large files efficiently
- Ensure you have sufficient storage space, as genome files can be quite large
- Consider using a genome browser or bioinformatics platform for easier management and analysis of the downloaded data
- Remember that these genomes are large datasets, so the download and processing may take some time depending on your
 internet connection and computer specifications
"""

from pathlib import Path

import requests


def download_genome(name: str, url: str, output_path: Path, expected_size: int) -> None:
    response = requests.get(url, timeout=300)
    response.raise_for_status()

    if len(response.content) != expected_size:
        raise ValueError(f"Expected size {expected_size} doesn't match actual size {len(response.content)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(response.content)
    print(f"Downloaded {name} genome")


if __name__ == "__main__":
    genomes = (
        ("Bonobo", "http://bioinf.eva.mpg.de/bonobo/contigs.fa.gz", Path("genomes/bonobo_contigs.fa.gz"), 771_200_739),
        (
            "Human",
            "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/hg38.fa.gz",
            Path("genomes/human_hg38.fa.gz"),
            872_409_395,
        ),
        (
            "Pig",
            "ftp://ftp.ensembl.org/pub/release-104/fasta/sus_scrofa/dna/Sus_scrofa.Sscrofa11.1.dna.toplevel.fa.gz",
            Path("genomes/pig_sscrofa11.1.fa.gz"),
            2_501_912_388,
        ),
    )

    for name, url, output_path, expected_size in genomes:
        if not output_path.exists():
            download_genome(name, url, output_path, expected_size)
        else:
            print(f"{name} genome already exists, skipping download")

    print("All downloads completed")
