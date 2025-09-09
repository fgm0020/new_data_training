# AI4S Paper Classifier Usage Guide

## Quick Start

To classify papers from NeurIPS 2024 and identify AI4S (AI for Science) papers:

```bash
python ai4s_classifier.py --neurips-dir NeurIPS_2024 --output neurips_2024_ai4s.csv
```

## Command Line Options

- `--ai4s-dir`: Directory with AI4S training data (default: AI4S_list)
- `--neurips-dir`: Directory with NeurIPS 2024 data (default: NeurIPS_2024)  
- `--output`: Output CSV file (default: neurips_2024_ai4s_classified.csv)

## Input Format

The classifier expects:
- **AI4S training data**: CSV files with columns `Title`, `Conference`, `Type`, `Application`, `MLTech`, `OpenReviewLink`
- **NeurIPS data**: CSV files with columns `type`, `name`, `virtualsite_url`, `speakers/authors`, `abstract`

## Output Format

Generated CSV with columns:
- `title`: Paper title
- `type`: Paper type (Poster, Oral, etc.)
- `virtualsite_url`: Link to paper
- `domain/subject`: Scientific domain (biology, chemistry, materials, physics, earth_climate, neuroscience, medical, social_science)

## Classification Methodology

### AI4S Inclusion Criteria:
1. ML techniques directly applied to scientific problems
2. Aimed at scientific discovery/modeling/prediction (not pure methodology)
3. Clear scientific domain application

### Scientific Domains:
- **Biology**: Protein, molecular, gene, cell biology, genomics
- **Chemistry**: Molecular design, chemical reactions, drug discovery
- **Materials**: Crystal, metal, solid-state physics, materials science
- **Physics**: Quantum mechanics, particle physics, high-energy physics
- **Earth/Climate**: Climate modeling, environmental science, atmospheric science
- **Neuroscience**: Brain modeling, neural systems, cognitive science
- **Medical**: Clinical applications, disease prediction, healthcare
- **Social Science**: Economics, human behavior, social systems

### Exclusion Criteria:
- Pure AI methodology (optimization, training algorithms)
- General computer vision/NLP without scientific focus
- Pure mathematical methods without scientific application
- Algorithm validation without scientific insights

## Example Results

For NeurIPS 2024, the classifier identified 317 AI4S papers (7.0% of 4,538 total papers) with this domain distribution:
- Biology: 103 papers (32.5%)
- Neuroscience: 77 papers (24.3%)
- Medical: 38 papers (12.0%)
- Social Science: 36 papers (11.4%)
- Chemistry: 33 papers (10.4%)
- Physics: 21 papers (6.6%)
- Earth/Climate: 7 papers (2.2%)
- Materials: 2 papers (0.6%)