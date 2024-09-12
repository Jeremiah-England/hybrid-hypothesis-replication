#!/bin/bash

set -euo pipefail

# Download genomes from the internet.
#
# To download the bonobo, human, and pig genomes, you'll need to access genomic databases and use bioinformatics tools.
# Here's a general guide on how to obtain these genomes:
#
# Bonobo Genome:
# The bonobo genome assembly is available from the Max Planck Institute for Evolutionary Anthropology. You can download it
# as follows:
# - Go to http://bioinf.eva.mpg.de/bonobo
# - Download the contigs, scaffolds, and chromosome-assigned scaffolds in FASTA format
# - Alternatively, access the scaffolds and contigs from GenBank (accession AJFE01000000)
#
# Human Genome:
# The human genome can be downloaded from several sources. A common resource is the UCSC Genome Browser:
# - Visit https://hgdownload.soe.ucsc.edu/downloads.html
# - Select the latest human genome assembly (e.g., GRCh38/hg38)
# - Download the desired file formats (FASTA, etc.)
#
# Pig Genome:
# The pig genome can be obtained from the Ensembl database:
# - Go to https://www.ensembl.org/Sus_scrofa/Info/Index
# - Click on "Download DNA sequence (FASTA)"
# - Select the desired assembly and download options
#
# General Tips:
# - Use command-line tools like wget or curl to download large files efficiently
# - Ensure you have sufficient storage space, as genome files can be quite large
# - Consider using a genome browser or bioinformatics platform for easier management and analysis of the downloaded data
# - Remember that these genomes are large datasets, so the download and processing may take some time depending on your
#  internet connection and computer specifications

# Download Bonobo genome
wget "http://bioinf.eva.mpg.de/bonobo/contigs.fa.gz" --output-document="genomes/bonobo_contigs.fa.gz"
# For some reason I had to download this one in the browser.

# Download Human genome
wget "https://hgdownload.soe.ucsc.edu/goldenPath/hg38/bigZips/latest/hg38.fa.gz" --output-document="genomes/human_hg38.fa.gz"

# Download Pig genome
wget "https://ftp.ensembl.org/pub/release-112/fasta/sus_scrofa/dna/Sus_scrofa.Sscrofa11.1.dna.toplevel.fa.gz" --output-document="genomes/pig_sscrofa11.1.fa.gz"

# Download the cow genome
wget "https://hgdownload.soe.ucsc.edu/goldenPath/bosTau9/bigZips/bosTau9.fa.gz" --output-document="genomes/cow_bosTau9.fa.gz"

echo "All downloads completed"