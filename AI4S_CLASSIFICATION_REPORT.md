# AI4S Classification Results for NeurIPS 2024

This document provides details about the AI4S (AI for Science) paper classification results for NeurIPS 2024.

## Summary Statistics

- **Total papers processed**: 4,538
- **AI4S papers identified**: 317 (7.0%)
- **Classification date**: $(date)

## Domain Distribution

| Domain | Count | Percentage |
|--------|-------|------------|
| Biology | 103 | 32.5% |
| Neuroscience | 77 | 24.3% |
| Medical/Healthcare | 38 | 12.0% |
| Social Science | 36 | 11.4% |
| Chemistry | 33 | 10.4% |
| Physics | 21 | 6.6% |
| Earth/Climate | 7 | 2.2% |
| Materials | 2 | 0.6% |

## AI4S Classification Criteria

### Inclusion Criteria:
- ML techniques directly used for scientific problems
- Aimed at advancing scientific discovery/modeling/prediction, not pure methodology
- Addresses specific scientific domains

### Scientific Domains Considered:
- Biology (protein, molecular, gene, cell biology, etc.)
- Chemistry (molecular design, chemical reactions, drug discovery, etc.)
- Materials (crystal, metal, solid-state physics, etc.) 
- Physics (quantum mechanics, particle physics, high-energy physics, etc.)
- Earth/Climate (climate modeling, environmental science, etc.)
- Neuroscience (brain modeling, neural systems, cognitive science, etc.)
- Medical/Healthcare (clinical applications, disease prediction, etc.)
- Social Science (economics, human behavior, social systems, etc.)

### Exclusion Criteria:
- Pure AI methodology papers (optimization, training algorithms, etc.)
- General computer vision/NLP applications without scientific domain focus
- Pure mathematical/computational methods without scientific application
- Algorithm validation without new scientific insights

## Validation

The classifier successfully identified 3 out of 4 manually curated AI4S papers from NeurIPS 2024:
- ✅ "Neural Pfaffians: Solving Many Many-Electron Schrödinger Equations" (Physics)
- ✅ "Graph Diffusion Transformers for Multi-Conditional Molecular Generation" (Chemistry)
- ✅ "MDAgents: An Adaptive Collaboration of LLMs for Medical Decision-Making" (Medical)
- ❌ "Learning Formal Mathematics From Intrinsic Motivation" (excluded as pure mathematics)

## Output Format

The final CSV file contains the following columns:
- `title`: Paper title
- `type`: Paper type (Poster, Oral, etc.)
- `virtualsite_url`: Link to the paper
- `domain/subject`: Classified scientific domain

## Files Generated

- `neurips_2024_ai4s_final.csv`: Final classification results
- `ai4s_classifier.py`: Classification script