from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict
import re

class EmbeddingEngine:
    def __init__(self):
        """Initialize with TF-IDF based similarity (offline, no internet required)."""
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.fitted = False
    
    def preprocess_text(self, text: str) -> str:
        """Clean and preprocess text."""
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text)
        # Convert to lowercase
        text = text.lower()
        return text.strip()
    
    def create_query_text(self, persona: str, job_to_be_done: str) -> str:
        """Create query text from persona and job."""
        query = f"{persona} {job_to_be_done}"
        return self.preprocess_text(query)
    
    def rank_sections_by_relevance(self, sections: List[Dict], persona: str, 
                                 job_to_be_done: str, top_k: int = 10) -> List[Dict]:
        """Rank sections by relevance using TF-IDF similarity."""
        if not sections:
            return []
        
        # Prepare texts
        query_text = self.create_query_text(persona, job_to_be_done)
        
        # Combine title and content for each section
        section_texts = []
        for section in sections:
            combined_text = f"{section['title']} {section['content']}"
            section_texts.append(self.preprocess_text(combined_text))
        
        # Add query to the corpus for fitting
        all_texts = [query_text] + section_texts
        
        # Fit TF-IDF vectorizer
        tfidf_matrix = self.vectorizer.fit_transform(all_texts)
        
        # Calculate similarities (query is first item)
        query_vector = tfidf_matrix[0:1]
        section_vectors = tfidf_matrix[1:]
        
        similarities = cosine_similarity(query_vector, section_vectors)[0]
        
        # Add relevance scores and rank
        for i, section in enumerate(sections):
            section['relevance_score'] = float(similarities[i])
            section['importance_rank'] = 0
        
        # Sort by relevance score (descending)
        ranked_sections = sorted(sections, key=lambda x: x['relevance_score'], reverse=True)
        
        # Assign importance ranks
        for i, section in enumerate(ranked_sections[:top_k]):
            section['importance_rank'] = i + 1
        
        return ranked_sections[:top_k]