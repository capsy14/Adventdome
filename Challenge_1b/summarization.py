from typing import List, Dict
import re

class TextSummarizer:
    def __init__(self):
        """Initialize text summarizer. Using extractive approach for efficiency."""
        pass
    
    def extractive_summarize(self, text: str, max_sentences: int = 3) -> str:
        """Simple extractive summarization based on sentence importance."""
        if not text or len(text.strip()) == 0:
            return ""
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= max_sentences:
            return text.strip()
        
        # Score sentences based on length and position
        scored_sentences = []
        for i, sentence in enumerate(sentences):
            # Simple scoring: prefer longer sentences and earlier sentences
            word_count = len(sentence.split())
            position_score = 1.0 / (i + 1)  # Earlier sentences get higher scores
            length_score = min(word_count / 20.0, 1.0)  # Normalize word count
            
            total_score = (position_score * 0.3) + (length_score * 0.7)
            scored_sentences.append((sentence, total_score))
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        top_sentences = scored_sentences[:max_sentences]
        
        # Reorder by original position
        sentence_positions = {sentence: sentences.index(sentence) 
                            for sentence, _ in top_sentences}
        top_sentences.sort(key=lambda x: sentence_positions[x[0]])
        
        return '. '.join([sentence for sentence, _ in top_sentences]) + '.'
    
    def create_subsection_analysis(self, ranked_sections: List[Dict], 
                                 persona: str, job_to_be_done: str) -> List[Dict]:
        """Create refined subsection analysis for top sections."""
        subsection_analysis = []
        
        # Focus on top 3-5 sections for detailed analysis
        top_sections = ranked_sections[:5]
        
        for section in top_sections:
            # Create a refined text that focuses on the persona's needs
            refined_text = self.refine_content_for_persona(
                section['content'], persona, job_to_be_done
            )
            
            subsection_analysis.append({
                "document": section['document'],
                "refined_text": refined_text,
                "page_number": section['page_number']
            })
        
        return subsection_analysis
    
    def refine_content_for_persona(self, content: str, persona: str, 
                                 job_to_be_done: str) -> str:
        """Refine content to be more relevant to the persona and job."""
        if not content or len(content.strip()) < 10:
            return content
        
        # Split content into meaningful sentences
        sentences = re.split(r'[.!?]+', content)
        sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        
        if not sentences:
            return content
        
        # Score sentences based on relevance keywords
        persona_keywords = self.extract_keywords(persona.lower())
        job_keywords = self.extract_keywords(job_to_be_done.lower())
        
        # Add common travel planning keywords for this use case
        if "travel" in persona.lower() or "trip" in job_to_be_done.lower():
            travel_keywords = ['hotel', 'restaurant', 'visit', 'attraction', 'beach', 'city', 
                             'tour', 'activity', 'group', 'friends', 'plan', 'day', 'night',
                             'food', 'place', 'location', 'cost', 'price', 'recommendation']
            job_keywords.extend(travel_keywords)
        
        scored_sentences = []
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Count keyword matches
            persona_matches = sum(1 for keyword in persona_keywords 
                                if keyword in sentence_lower)
            job_matches = sum(1 for keyword in job_keywords 
                            if keyword in sentence_lower)
            
            # Length and content quality scoring
            word_count = len(sentence.split())
            length_score = min(word_count / 20.0, 1.0) if word_count >= 5 else 0
            
            # Avoid very short fragments
            if word_count < 5:
                continue
                
            # Calculate total relevance score
            relevance_score = (persona_matches * 0.3) + (job_matches * 0.5) + (length_score * 0.2)
            scored_sentences.append((sentence, relevance_score))
        
        if not scored_sentences:
            # Fallback to original content if no good sentences found
            return self.extractive_summarize(content, max_sentences=3)
        
        # Sort by score and take top sentences
        scored_sentences.sort(key=lambda x: x[1], reverse=True)
        
        # Select top sentences up to word limit
        selected_sentences = []
        total_words = 0
        max_words = 250
        
        for sentence, score in scored_sentences:
            sentence_words = len(sentence.split())
            if total_words + sentence_words <= max_words and len(selected_sentences) < 5:
                selected_sentences.append(sentence)
                total_words += sentence_words
            if total_words >= max_words or len(selected_sentences) >= 5:
                break
        
        if not selected_sentences:
            return self.extractive_summarize(content, max_sentences=2)
        
        # Join sentences and clean up
        refined_text = '. '.join(selected_sentences)
        if not refined_text.endswith('.'):
            refined_text += '.'
            
        return refined_text
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        # Remove common stop words and extract meaningful terms
        stop_words = {'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 
                     'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 
                     'that', 'the', 'to', 'was', 'will', 'with', 'the', 'this',
                     'that', 'these', 'those', 'i', 'me', 'my', 'myself', 'we',
                     'our', 'ours', 'ourselves', 'you', 'your', 'yours'}
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return list(set(keywords))  # Remove duplicates