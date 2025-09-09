#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import csv
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple, Set
import argparse

class AI4SClassifier:
    """
    Classifier for identifying AI4S (AI for Science) papers based on specific criteria.
    
    AI4S Inclusion Criteria:
    - ML techniques directly used for scientific problems
    - Aimed at advancing scientific discovery/modeling/prediction, not pure methodology
    
    Domains: biology, chemistry, materials, physics, earth_climate, neuroscience, medical/healthcare, social_science
    
    Exclusion Criteria:
    - Neural Applications (pure AI applications/engineering, not serving specific scientific problems)
    - Computational Methods (pure methodology/optimization/training tricks/theoretical bounds)
    - Mathematical Modeling (only mathematical/numerical methods without new scientific insights)
    - Experimental Validation (only algorithm performance validation without new conclusions about scientific objects)
    """
    
    def __init__(self):
        # Domain keywords for classification
        self.domain_keywords = {
            'biology': {
                'protein', 'molecular', 'gene', 'genetic', 'genomics', 'cell', 'cellular', 'antibody', 
                'alphafold', 'ligand', 'binding', 'enzyme', 'dna', 'rna', 'sequence', 'phylogenetic',
                'evolution', 'organism', 'species', 'microbiome', 'bacteria', 'virus', 'biological',
                'biomedical', 'biochemical', 'bioinformatics', 'biotechnology', 'life', 'living'
            },
            'chemistry': {
                'chemical', 'molecule', 'molecular', 'atom', 'atomic', 'reaction', 'catalyst', 
                'synthesis', 'compound', 'drug', 'pharmaceutical', 'material', 'crystal', 
                'density functional theory', 'dft', 'quantum chemistry', 'periodic table',
                'electrochemical', 'organic', 'inorganic', 'polymer', 'solvent', 'ion'
            },
            'materials': {
                'material', 'crystal', 'crystalline', 'solid', 'metal', 'metallic', 'alloy',
                'semiconductor', 'ceramic', 'polymer', 'composite', 'nanomaterial', 'nanotechnology',
                'surface', 'interface', 'mechanical', 'thermal', 'electrical', 'magnetic',
                'glass', 'powder', 'coating', 'fabrication', 'manufacturing'
            },
            'physics': {
                'physics', 'quantum', 'particle', 'electron', 'photon', 'wave', 'field',
                'schrödinger', 'hamiltonian', 'electromagnetic', 'optics', 'laser', 'plasma',
                'condensed matter', 'statistical mechanics', 'thermodynamic', 'energy',
                'force', 'momentum', 'relativity', 'nuclear', 'astrophysics', 'cosmology'
            },
            'earth_climate': {
                'climate', 'weather', 'atmospheric', 'ocean', 'oceanic', 'earth', 'geophysics',
                'geology', 'seismic', 'earthquake', 'volcano', 'environmental', 'ecosystem',
                'carbon', 'greenhouse', 'temperature', 'precipitation', 'ice', 'glacier',
                'satellite', 'remote sensing', 'geography', 'hydrology', 'meteorology'
            },
            'neuroscience': {
                'neural', 'neuron', 'brain', 'cognitive', 'cortex', 'neuroscience', 'neurological',
                'eeg', 'fmri', 'connectome', 'synapse', 'axon', 'dendrite', 'hippocampus',
                'memory', 'learning', 'attention', 'perception', 'consciousness', 'behavior',
                'psychiatric', 'neuroimaging', 'pathway', 'neural network'
            },
            'medical': {
                'medical', 'clinical', 'patient', 'disease', 'diagnosis', 'treatment', 'therapy',
                'health', 'healthcare', 'hospital', 'doctor', 'physician', 'medicine', 'drug',
                'pharmaceutical', 'vaccine', 'surgery', 'cancer', 'tumor', 'pathology',
                'epidemiology', 'public health', 'biomarker', 'imaging', 'radiology'
            },
            'social_science': {
                'social', 'society', 'human', 'behavior', 'psychology', 'economic', 'economics',
                'political', 'sociology', 'anthropology', 'demographic', 'population', 'culture',
                'communication', 'education', 'policy', 'governance', 'urban', 'rural'
            }
        }
        
        # Exclusion keywords that indicate non-AI4S papers
        self.exclusion_keywords = {
            'pure_methodology': {
                'optimization', 'training', 'gradient', 'convergence', 'regularization',
                'generalization', 'overfitting', 'hyperparameter', 'architecture search',
                'neural architecture', 'pruning', 'quantization', 'compression', 'efficiency',
                'acceleration', 'speedup', 'memory', 'computational complexity', 'theoretical',
                'bound', 'analysis', 'framework', 'algorithm', 'method'
            },
            'pure_ai_applications': {
                'recommendation', 'computer vision', 'natural language processing', 'nlp',
                'image classification', 'object detection', 'segmentation', 'generation',
                'gan', 'diffusion model', 'transformer', 'attention', 'self-supervised',
                'unsupervised', 'reinforcement learning', 'multi-agent', 'robotics'
            }
        }
        
        # Scientific indicators that suggest real scientific application
        self.scientific_indicators = {
            'discovery', 'prediction', 'modeling', 'simulation', 'analysis', 'understanding',
            'mechanism', 'phenomenon', 'system', 'property', 'behavior', 'structure',
            'function', 'process', 'dynamics', 'interaction', 'relationship', 'effect',
            'design', 'generation', 'identification', 'characterization', 'optimization'
        }
        
    def load_training_data(self, ai4s_dir: str) -> List[Dict]:
        """Load all manually curated AI4S training data."""
        training_data = []
        ai4s_path = Path(ai4s_dir)
        
        for csv_file in ai4s_path.glob("*.csv"):
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Title'):  # Skip empty rows
                            training_data.append(row)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")
                
        return training_data
    
    def extract_keywords_from_training(self, training_data: List[Dict]) -> Dict[str, Set[str]]:
        """Extract domain-specific keywords from training data."""
        domain_keywords = {}
        
        for paper in training_data:
            application = paper.get('Application', '').lower()
            title = paper.get('Title', '').lower()
            
            # Map training data applications to our standardized domains
            domain_mapping = {
                'biology': 'biology',
                'chemistry': 'chemistry', 
                'materials': 'materials',
                'physics': 'physics',
                'medical': 'medical',
                'math': 'physics',  # Mathematical physics often maps to physics
                'general': None  # Skip general applications
            }
            
            mapped_domain = domain_mapping.get(application)
            if mapped_domain:
                if mapped_domain not in domain_keywords:
                    domain_keywords[mapped_domain] = set()
                
                # Extract keywords from title
                words = re.findall(r'\b\w+\b', title)
                for word in words:
                    if len(word) > 3:  # Only meaningful words
                        domain_keywords[mapped_domain].add(word)
        
        return domain_keywords
    
    def classify_paper(self, title: str, abstract: str) -> Tuple[bool, str]:
        """
        Classify if a paper is AI4S and determine its domain.
        
        Returns:
            (is_ai4s, domain) where is_ai4s is bool and domain is string or None
        """
        text = f"{title} {abstract}".lower()
        
        # Check for exclusion criteria first
        if self._is_excluded(text):
            return False, None
        
        # Check for scientific domain and indicators
        domain = self._identify_domain(text)
        has_scientific_indicators = self._has_scientific_indicators(text)
        has_strong_domain_indicators = self._has_strong_domain_indicators(text, domain)
        
        # A paper is AI4S if it has domain relevance, scientific indicators, and strong domain-specific content
        is_ai4s = (domain is not None and 
                  has_scientific_indicators and 
                  has_strong_domain_indicators)
        
        return is_ai4s, domain
    
    def _is_excluded(self, text: str) -> bool:
        """Check if paper should be excluded based on exclusion criteria."""
        # Stronger exclusion patterns that are unlikely to be scientific
        strong_exclusions = [
            'federated learning', 'computer vision', 'natural language processing', 
            'recommendation system', 'neural architecture search', 'pruning',
            'quantization', 'compression', 'generative adversarial', 
            'self-supervised', 'unsupervised learning', 'representation learning'
        ]
        
        # Check for exclusions but be more lenient for scientific contexts
        for exclusion in strong_exclusions:
            if exclusion in text:
                # Check if it's being applied to a scientific domain
                has_strong_science_context = False
                scientific_terms = [
                    'molecule', 'molecular', 'protein', 'cell', 'gene', 'quantum', 
                    'electron', 'atom', 'chemical', 'biological', 'medical', 'clinical',
                    'physics', 'chemistry', 'biology', 'material', 'crystal', 'brain'
                ]
                
                science_count = sum(1 for term in scientific_terms if term in text)
                if science_count >= 2:  # Has clear scientific context
                    has_strong_science_context = True
                
                if not has_strong_science_context:
                    return True
        
        # More specific exclusions for pure methodology
        pure_methodology_phrases = [
            'theoretical analysis of', 'convergence analysis', 'optimization algorithm',
            'training algorithm', 'learning algorithm', 'framework for'
        ]
        
        for phrase in pure_methodology_phrases:
            if phrase in text:
                # Check if followed by scientific application
                scientific_applications = [
                    'molecular', 'protein', 'gene', 'quantum', 'medical', 'clinical',
                    'biological', 'chemical', 'material', 'climate', 'brain'
                ]
                has_scientific_application = any(app in text for app in scientific_applications)
                if not has_scientific_application:
                    return True
            
        return False
    
    def _identify_domain(self, text: str) -> str:
        """Identify the scientific domain of the paper."""
        domain_scores = {}
        
        for domain, keywords in self.domain_keywords.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    # Give higher weight to more specific scientific terms
                    if len(keyword) > 6:  # Longer, more specific terms
                        score += 2
                    else:
                        score += 1
                    
            if score >= 3:  # Require minimum threshold
                domain_scores[domain] = score
        
        if not domain_scores:
            return None
            
        # Return domain with highest score
        return max(domain_scores, key=domain_scores.get)
    
    def _has_strong_domain_indicators(self, text: str, domain: str) -> bool:
        """Check if paper has strong domain-specific indicators."""
        if not domain:
            return False
            
        # Domain-specific strong indicators
        strong_indicators = {
            'biology': {'protein', 'gene', 'cell', 'molecular', 'organism', 'biological', 'dna', 'rna'},
            'chemistry': {'chemical', 'molecule', 'reaction', 'compound', 'synthesis', 'molecular', 'drug'},
            'materials': {'material', 'crystal', 'metal', 'solid', 'mechanical'},
            'physics': {'quantum', 'particle', 'electron', 'field', 'physics', 'schrödinger', 'hamiltonian', 'wave'},
            'earth_climate': {'climate', 'weather', 'atmospheric', 'environmental'},
            'neuroscience': {'brain', 'neural', 'neuron', 'cognitive', 'connectome'},
            'medical': {'medical', 'clinical', 'patient', 'disease', 'health'},
            'social_science': {'social', 'economic', 'behavior', 'human', 'society'}
        }
        
        if domain not in strong_indicators:
            return False
            
        # Count strong indicators for the identified domain
        indicator_count = sum(1 for indicator in strong_indicators[domain] if indicator in text)
        return indicator_count >= 2
    
    def _has_scientific_indicators(self, text: str) -> bool:
        """Check if paper has indicators of scientific research."""
        indicator_count = 0
        
        for indicator in self.scientific_indicators:
            if indicator in text:
                indicator_count += 1
        
        # Require at least 2 scientific indicators
        return indicator_count >= 2

def load_neurips_data(neurips_dir: str) -> List[Dict]:
    """Load all NeurIPS 2024 CSV files."""
    papers = []
    neurips_path = Path(neurips_dir)
    
    for csv_file in neurips_path.glob("*.csv"):
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('name'):  # Skip empty rows
                        papers.append(row)
        except Exception as e:
            print(f"Error reading {csv_file}: {e}")
    
    return papers

def main():
    parser = argparse.ArgumentParser(description='Classify NeurIPS 2024 papers for AI4S')
    parser.add_argument('--ai4s-dir', default='AI4S_list', help='Directory with AI4S training data')
    parser.add_argument('--neurips-dir', default='NeurIPS_2024', help='Directory with NeurIPS 2024 data')
    parser.add_argument('--output', default='neurips_2024_ai4s_classified.csv', help='Output CSV file')
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = AI4SClassifier()
    
    # Load training data (optional, mainly for analysis)
    print("Loading AI4S training data...")
    training_data = classifier.load_training_data(args.ai4s_dir)
    print(f"Loaded {len(training_data)} training examples")
    
    # Load NeurIPS 2024 data
    print("Loading NeurIPS 2024 data...")
    neurips_papers = load_neurips_data(args.neurips_dir)
    print(f"Loaded {len(neurips_papers)} NeurIPS 2024 papers")
    
    # Classify papers
    print("Classifying papers...")
    ai4s_papers = []
    
    for paper in neurips_papers:
        title = paper.get('name', '')
        abstract = paper.get('abstract', '')
        
        is_ai4s, domain = classifier.classify_paper(title, abstract)
        
        if is_ai4s:
            ai4s_papers.append({
                'title': title,
                'type': paper.get('type', ''),
                'virtualsite_url': paper.get('virtualsite_url', ''),
                'domain/subject': domain
            })
    
    # Save results
    print(f"Found {len(ai4s_papers)} AI4S papers out of {len(neurips_papers)} total papers")
    
    with open(args.output, 'w', encoding='utf-8', newline='') as f:
        fieldnames = ['title', 'type', 'virtualsite_url', 'domain/subject']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ai4s_papers)
    
    print(f"Results saved to {args.output}")
    
    # Print domain distribution
    domain_counts = {}
    for paper in ai4s_papers:
        domain = paper['domain/subject']
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    
    print("\nDomain distribution:")
    for domain, count in sorted(domain_counts.items()):
        print(f"  {domain}: {count}")

if __name__ == "__main__":
    main()