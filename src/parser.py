import json
import logging
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Set
import requests
import sys
import os
from collections import defaultdict
from dataclasses import dataclass, asdict
from thefuzz import fuzz

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class Book:
    """Class to represent a book of the Histories."""
    number: str # Roman numeral
    content: str
    title: str

@dataclass
class QuoteQualityMetrics:
    grammatical_completeness: float  # Based on sentence structure
    context_relevance: float        # How well context matches
    attribution_confidence: float    # Speaker attribution confidence
    text_cleanliness: float        # Absence of editorial marks

@dataclass
class Quote:
    """Class for storing quote information."""
    speaker: str
    text: str
    book: str
    context_before: str
    context_after: str
    pattern_matched: str
    confidence: float = 1.0

class DialogueContext:
    """Manages dialogue context and speaker tracking."""
    def __init__(self, text: str, characters: Set[str], window_size: int = 500):
        self.text = text
        self.characters = characters
        self.window_size = window_size
        self.current_speaker = None
        self.last_quote_end = 0
        self.speech_indicators = [
            "said", "spoke", "replied", "answered", "declared",
            "made answer", "addressed", "responded", "called out",
            "cried", "exclaimed", "proclaimed", "told", "asked",
            "commanded", "ordered", "shouted", "stated",
            "message", "word", "answered", "continued", "began",
            "whispered", "remarked", "announced"
        ]
        
    def find_speaker_in_context(self, position: int) -> Optional[str]:
        """Look backwards from position to find the most recent speaker."""
        start = max(0, position - self.window_size)
        context = self.text[start:position]
        
        # Look for character names before speech indicators
        candidates = []
        for char in sorted(self.characters, key=len, reverse=True):
            if char in context:
                char_pos = context.rfind(char)
                after_char = context[char_pos:].lower()
                if any(indicator in after_char for indicator in self.speech_indicators):
                    candidates.append((char_pos, char))
        
        # Return the most recent speaker found
        if candidates:
            return sorted(candidates, reverse=True)[0][1]
        return None
    
    def get_context(self, start: int, end: int) -> Tuple[str, str]:
        """Get text context before and after a quote."""
        context_start = max(0, start - self.window_size)
        context_end = min(len(self.text), end + self.window_size)
        
        before = self.text[context_start:start].strip()
        after = self.text[end:context_end].strip()
        
        return before, after

class HerodotusParser:
    def __init__(self):
        self.urls = [
            "https://www.gutenberg.org/cache/epub/2707/pg2707.txt",  # Volume 1
            "https://www.gutenberg.org/cache/epub/2456/pg2456.txt"   # Volume 2
        ]
        self.raw_texts = []
        self.books: Dict[str, Book] = {}
        self.quotes: List[Quote] = []
        self.debug_info = defaultdict(list)
        self.quote_deduplicator = QuoteDeduplicator()
        
        # Load character data
        try:
            with open("characters.json", "r", encoding="utf-8") as f:
                self.character_data = json.load(f)
                logger.info(f"Loaded {len(self.character_data)} characters from characters.json")
        except Exception as e:
            logger.error(f"Error loading characters.json: {e}")
            raise

        # Initialize character sets
        self.characters: Set[str] = set()
        self.character_variations: Dict[str, List[str]] = {}
        self.process_character_data()

        # Initialize directories
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        
        # Speech indicators
        self.speech_indicators = [
            r"said", r"spoke", r"replied", r"answered", r"declared",
            r"made answer", r"addressed", r"responded", r"called out",
            r"cried", r"exclaimed", r"proclaimed", r"told", r"asked",
            r"commanded", r"ordered", r"shouted", r"stated"
        ]
        
        # Compile speech pattern
        self.speech_pattern = f"(?:{"|".join(self.speech_indicators)})"
        
        # Quote patterns
        base_patterns = [
            # Split quotes with intervening attribution
            (fr'"([^"]+)"\s*,?\s*{self.speech_pattern}\s+(?:he|she).*?"([^"]+)"', 
            "split_quote"),
                
            # Basic attribution with quotes
            (r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[:\.,]?\s*"([^"]+)"',
            "basic_quote"),
            
            # Quote first then speaker
            (fr'"([^"]+)"\s*{self.speech_pattern}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            "quote_first"),
                
            # Then/Thus pattern
            (r'(?:Then|Thus)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*[:\.,]?\s*"([^"]+)"',
            "then_thus")
        ]
    
        # Add delayed attribution patterns
        self.quote_patterns = base_patterns + [(pattern, name) for pattern, name, _ in self.get_delayed_attribution_patterns()]

        # Statistics
        self.stats = defaultdict(int)

    def process_character_data(self):
        """Process and validate character data."""
        for char_data in self.character_data:
            name = char_data["name"]
            self.characters.add(name)
            variations = char_data.get("variations", [])
            self.character_variations[name] = variations
            self.characters.update(variations)
        
        logger.info(f"Processed {len(self.characters)} total character names and variations")

    def get_delayed_attribution_patterns(self) -> List[Tuple[str, str, float]]:
        """Enhanced patterns for quote detection."""
        patterns = [
            # Action-based attribution
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?(?:turning|looking|seeing)[^"]*?{self.speech_pattern}[^"]*?"(?P<quote>[^"]+)"', 
            "delayed_attribution_action", 
            0.85),
        
            # State-based attribution
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?(?:silent|angry|pleased)[^"]*?{self.speech_pattern}[^"]*?"(?P<quote>[^"]+)"',
            "delayed_attribution_state",
            0.82),
        
            # Temporal attribution
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?(?:when|after|while)[^"]*?{self.speech_pattern}[^"]*?"(?P<quote>[^"]+)"',
            "delayed_attribution_temporal",
            0.80),

            # Indirect speech
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?(?:message|word)[^"]*?"(?P<quote>[^"]+)"',
            "delayed_indirect_speech",
            0.78),
            
            # Group dialogue
            (fr'(?:they|the\s+[A-Z][a-z]+)[^"]*?to\s+(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?"(?P<quote>[^"]+)"',
            "group_dialogue",
            0.75),
        
            # Original pattern as fallback
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?{self.speech_pattern}[^"]*?"(?P<quote>[^"]+)"',
            "delayed_attribution_basic",
            0.75),

            # Conversation markers
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?(?:conversation|discussion)[^"]*?"(?P<quote>[^"]+)"',
            "conversation_marker",
            0.8),

            # Response patterns
            (fr'(?P<speaker>[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)[^"]*?(?:answer|response)[^"]*?"(?P<quote>[^"]+)"',
            "response_pattern",
            0.85)
        ]
        return patterns

    def fetch_texts(self) -> None:
        """Fetch texts from both Gutenberg volumes."""
        for url in self.urls:
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                self.raw_texts.append(response.text)
                logger.info(f"Successfully fetched text from {url}")
            except Exception as e:
                logger.error(f"Failed to fetch text from {url}: {str(e)}")
                raise

    def clean_texts(self) -> str:
        """Clean the texts while preserving book headers."""
        if not self.raw_texts:
            raise ValueError("No texts to clean. Did you run fetch_texts()?")

        combined_text = ""
        for i, text in enumerate(self.raw_texts, 1):
            try:
                # Find core content
                start_marker = "*** START OF THE PROJECT GUTENBERG EBOOK"
                end_marker = "*** END OF THE PROJECT GUTENBERG EBOOK"
                
                start_idx = text.find(start_marker)
                end_idx = text.find(end_marker)

                if start_idx == -1 or end_idx == -1:
                    raise ValueError(f"Could not find markers in volume {i}")
                
                text = text[start_idx:end_idx]
                
                # Clean the text
                text = re.sub(r'\[\s*\d+\s*\][^\n]*\n', '', text)  # Remove footnotes
                text = re.sub(r'\{[^}]*\}', '', text)              # Remove Greek
                text = re.sub(r'\s+', ' ', text)                   # Normalize whitespace
                text = text.strip()
                
                combined_text += text + "\n\n"
                logger.info(f"Successfully cleaned volume {i}")
                
            except Exception as e:
                logger.error(f"Error cleaning volume {i}: {str(e)}")
                raise
                
        return combined_text

    def split_into_books(self, text: str) -> None:
        """Split text into books using Book dataclass."""
        try:
            book_pattern = r"BOOK\s+([IVX]+)\.?\s+THE\s+([^B]+)BOOK\s+OF\s+THE\s+HISTORIES"
            book_positions = []

            # Find all book positions
            for match in re.finditer(book_pattern, text, re.MULTILINE | re.IGNORECASE):
                book_num = match.group(1)
                book_title = match.group(2).strip()
                start_pos = match.start()
                book_positions.append((book_num, book_title, start_pos))
            
            # Sort positions
            book_positions.sort(key=lambda x: x[2])

            # Extract each book's content
            for i, (book_num, book_title, start_pos) in enumerate(book_positions):
                end_pos = book_positions[i + 1][2] if i + 1 < len(book_positions) else len(text)
                content = text[start_pos:end_pos].strip()
                
                self.books[book_num] = Book(
                    number=book_num,
                    content=content,
                    title=book_title
                )
            
            logger.info(f"Split text into {len(self.books)} books")
            
        except Exception as e:
            logger.error(f"Error splitting books: {str(e)}")
            raise

    def clean_quote(self, quote: str) -> str:
        # Add better editorial mark handling
        quote = re.sub(r'\[\d+\]', '', quote)  # Remove reference numbers
        quote = re.sub(r'\([^)]*\)', '', quote)  # Remove parentheticals
        quote = re.sub(r'\s+', ' ', quote)       # Normalize whitespace
        return quote.strip('"\' []')
    
    def resolve_speaker(self, speaker: str, context: str) -> Optional[str]:
        """Enhanced speaker resolution with fuzzy matching."""
        # Direct match
        if speaker in self.characters:
            return speaker
            
        # Fuzzy matching for names
        best_match = None
        best_score = 0
        for char_name in self.characters:
            score = fuzz.ratio(speaker, char_name)
            if score > 85 and score > best_score:
                best_match = char_name
                best_score = score
        if best_match:
            return best_match
                
        # Check variations with stronger context validation
        for char_data in self.character_data:
            if speaker in char_data["variations"]:
                # Verify with surrounding context
                if any(indicator in context.lower() for indicator in self.speech_indicators):
                    return char_data["name"]
        
        # Look for contextual clues with expanded window
        words = context.split()
        for i, word in enumerate(words):
            if word in self.characters:
                # Check if there's a speech indicator within 10 words
                nearby_words = ' '.join(words[max(0, i-10):min(len(words), i+10)]) 
                if any(indicator in nearby_words.lower() for indicator in self.speech_indicators):
                    return word
        
        return None

    def is_valid_quote(self, quote: str) -> bool:
        """Enhanced quote validation with positive indicators."""
        # Too short
        if len(quote.split()) < 4:  # Reduced minimum length
            return False
            
        # Structural issues
        if quote.isupper() or quote.count('[') != quote.count(']'):
            return False
            
        # Check for editorial content
        if re.match(r'^\d+\.|\[|\(', quote):
            return False
        if any(marker in quote.upper() for marker in ["NOTE:", "BOOK", "CHAPTER", "MS", "MSS"]):
            return False
            
        # Strong positive indicators
        if any(indicator in quote.lower() for indicator in [
            "thus", "spoke", "said", "replied", "answered",
            "declared", "commanded", "asked"
        ]):
            return True
            
        # Check for sentence completeness
        sentences = re.split(r'[.!?]+', quote)
        complete_sentences = [s for s in sentences if len(s.split()) >= 3]
        if len(complete_sentences) / len(sentences) > 0.5:
            return True
            
        return len(quote.split()) >= 4  # Final length check

    def text_similarity(self, text1: str, text2:str) -> float:
        """Calculate similarity ratio b/w two texts using difflib."""
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def _is_split_quote(self, quote: Quote) -> bool:
        """Check if this quote appears to be part of a longer speech."""
        continuation_markers = [
            "Thus having said",
            "Having so said",
            "After this",
            "Then",
            "; and"
        ]

        for marker in continuation_markers:
            if (marker in quote.context_before.split(".")[-1] or
                marker in quote.context_after.split(".")[0]):
                return True
            return False
        
    def _merge_split_quotes(self, quote: Quote) -> bool:
        """Attempt to merge related quote fragments."""
        for existing_quote in self.seen_quotes.values():
            if (existing_quote.speaker == quote.speaker and
                existing_quote.book == quote.book and 
                abs(len(existing_quote.context_before) - len(quote.context_before)) < 1000):

                merged_text = f"{existing_quote.text}\n\n{quote.text}"
                merged_confidence = max(existing_quote.confidence, quote.confidence)

                merged_quote = Quote(
                    speaker=quote.speaker,
                    text=merged_text,
                    book=quote.book,
                    context_before=min(existing_quote.context_before, quote.context_before),
                    context_after=max(existing_quote.context_after, quote.context_after),
                    pattern_matched=quote.pattern_matched,
                    confidence=merged_confidence
                )

                self.seen_quotes[merged_text] = merged_quote
                return True
            return False
    
    def is_duplicate_quote(self, quote: Quote) -> bool:
        """Enhanced duplicate detection."""
        # Check if exact duplicate
        if quote.text in self.seen_quotes:
            existing = self.seen_quotes[quote.text]

            # Same context - true duplicate
            if self._same_context(existing, quote):
                return quote.confidence < existing.confidence
        
            # Different context but similar content
            if self._is_reference(existing, quote):
                self.references.add((existing, quote))
                return False
    
        # Check for split quotes that should be merged
        if self._is_split_quote(quote):
            return self._merge_split_quotes(quote)
    
        self.seen_quotes[quote.text] = quote
        return False
        
    def _same_context(self, q1: Quote, q2: Quote) -> bool:
        """Check if quotes appear in same context."""
        return (q1.book == q2.book and
                q1.context_before[:100] == q2.context_before[:100])
    
    def _is_reference(self, q1: Quote, q2: Quote) -> bool:
        """Check if one quote is referencing the other."""
        return (q1.book != q2.book or
                abs(len(q1.context_before) - len(q2.context_before)) > 1000)

    def extract_quotes(self, book: Book) -> None:
        """Extract quotes from a book."""
        if not book.content:
            raise ValueError(f"Empty content for Book {book.number}")
        
        dialogue_context = DialogueContext(book.content, self.characters)
        book_stats = defaultdict(int)
        seen_quotes = set()

        # Get delayed attribution patterns with their confidence values
        delayed_patterns = {name: conf for _, name, conf in self.get_delayed_attribution_patterns()}

        for pattern, pattern_name in self.quote_patterns:
            matches = list(re.finditer(pattern, book.content, re.DOTALL))
            book_stats[f"{pattern_name}_attempts"] = len(matches)
            
            for match in matches:
                try:
                    # Extract quote based on pattern type
                    if pattern_name == "split_quote":
                        quote = match.group(1) + " " + match.group(2)
                        speaker = dialogue_context.find_speaker_in_context(match.start())
                    elif pattern_name == "quote_first":
                        quote = match.group(1)
                        speaker = match.group(2)
                    else:
                        speaker = match.group(1)
                        quote = match.group(2)

                    # Clean quote
                    quote = self.clean_quote(quote)
                    
                    # Skip if invalid
                    if not self.is_valid_quote(quote):
                        book_stats["invalid_quote"] += 1
                        continue

                    # Get context
                    context_before, context_after = dialogue_context.get_context(
                        match.start(), match.end())

                    # Resolve speaker
                    resolved_speaker = self.resolve_speaker(speaker, context_before)
                    if not resolved_speaker:
                        book_stats["unresolved_speaker"] += 1
                        continue

                    # Check for duplicates
                    if (resolved_speaker, quote) in seen_quotes:
                        book_stats["duplicate"] += 1
                        continue

                    # Calculate confidence
                    confidence = 1.0
                    # Pattern-based confidence
                    if pattern_name.startswith("delayed_attribution"):
                        confidence = delayed_patterns.get(pattern_name, 0.75)
                    elif pattern_name == "basic_quote":
                        confidence = 1.0  # Direct attribution with quotes is most reliable
                    elif pattern_name == "split_quote":
                        confidence = 0.95  # Split quotes are very reliable but need reconstruction
                    elif pattern_name == "quote_first":
                        confidence = 0.80  # Quote-first patterns can be ambiguous
                        
                    # Speaker resolution penalties
                    if speaker != resolved_speaker:
                        if speaker in self.character_variations.get(resolved_speaker, []):
                            confidence *= 0.95  # Small penalty for known variations
                        else:
                            confidence *= 0.85  # Larger penalty for context-based resolution

                    # Context-based adjustments
                    if any(indicator in context_before.lower() for indicator in 
                        ["answered", "replied", "made answer"]):
                        confidence *= 1.1  # Boost for strong dialogue indicators

                    # Store quote
                    if not self.quote_deduplicator.is_duplicate(Quote(
                        speaker=resolved_speaker,
                        text=quote,
                        book=book.number,
                        context_before=context_before,
                        context_after=context_after,
                        pattern_matched=pattern_name,
                        confidence=confidence
                    )):
                        seen_quotes.add((resolved_speaker, quote))
                        self.quotes.append(Quote(
                            speaker=resolved_speaker,
                            text=quote,
                            book=book.number,
                            context_before=context_before,
                            context_after=context_after,
                            pattern_matched=pattern_name,
                            confidence=confidence
                        ))
                        book_stats[f"{pattern_name}_success"] += 1

                except Exception as e:
                    logger.error(f"Error processing match in {pattern_name}: {e}")
                    self.debug_info["errors"].append({
                        "pattern": pattern_name,
                        "error": str(e),
                        "text": match.group(0)[:100]
                    })

        # Log book statistics
        logger.info(f"\nBook {book.number} Statistics:")
        for stat, count in book_stats.items():
            logger.info(f"  {stat}: {count}")
            self.stats[f"{book.number}_{stat}"] += count
            self.debug_info.update(self.quote_deduplicator.debug_info)

    def process_books(self):
        """Process all books in order."""
        roman_numerals = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX']
        
        for numeral in roman_numerals:
            if numeral in self.books:
                book = self.books[numeral]
                logger.info(f"\nProcessing Book {book.number}: {book.title}")
                self.extract_quotes(book)

    def assess_quote_quality(self, quote: Quote) -> QuoteQualityMetrics:
        """Assess the quality of a quote based on multiple metrics."""
        # Calculate grammatical completeness
        sentences = re.split(r'[.!?]+', quote.text)
        complete_sentences = [s for s in sentences if len(s.split()) > 3]
        grammatical_score = len(complete_sentences) / len(sentences) if sentences else 0.0

        # Calculate context relevance
        context_words = set(quote.context_before.split() + quote.context_after.split())
        quote_words = set(quote.text.split())
        context_overlap = len(quote_words.intersection(context_words)) / len(quote_words)
        
        # Calculate attribution confidence based on pattern and context
        attribution_score = quote.confidence
        if any(indicator in quote.context_before.lower() 
               for indicator in self.speech_indicators):
            attribution_score *= 1.1

        # Calculate text cleanliness
        editorial_marks = sum(1 for c in quote.text if c in '[](){}')
        cleanliness_score = 1.0 - (editorial_marks / len(quote.text))

        return QuoteQualityMetrics(
            grammatical_completeness=min(1.0, grammatical_score),
            context_relevance=min(1.0, context_overlap),
            attribution_confidence=min(1.0, attribution_score),
            text_cleanliness=min(1.0, cleanliness_score)
        )

    def save_data(self) -> None:
        """Save quotes and debug information."""
        try:
            # Convert quotes to dictionaries and add quality metrics
            quotes_data = []
            for quote in self.quotes:
                quote_dict = asdict(quote)
                quote_dict['quality_metrics'] = asdict(self.assess_quote_quality(quote))
                quotes_data.append(quote_dict)
            
            # Sort by combined quality score
            quotes_data.sort(key=lambda x: (
                x['confidence'] + sum(x['quality_metrics'].values()) / 4.0
            ), reverse=True)
            
            # Save quotes
            quotes_file = self.data_dir / "quotes.json"
            with open(quotes_file, "w", encoding='utf-8') as f:
                json.dump(quotes_data, f, indent=2, ensure_ascii=False)
            
            # Save debug info
            debug_file = self.data_dir / "debug_info.json"
            with open(debug_file, "w", encoding='utf-8') as f:
                json.dump(dict(self.debug_info), f, indent=2, ensure_ascii=False)
            
            # Save detailed quotes file with context
            detailed_file = self.data_dir / "quotes_with_context.txt"
            with open(detailed_file, "w", encoding='utf-8') as f:
                for quote in self.quotes:
                    f.write(f"\nSpeaker: {quote.speaker}\n")
                    f.write(f"Book: {quote.book}\n")
                    f.write(f"Pattern: {quote.pattern_matched}\n")
                    f.write(f"Confidence: {quote.confidence}\n")
                    f.write("Context Before:\n")
                    f.write(f"{quote.context_before}\n")
                    f.write("Quote:\n")
                    f.write(f"{quote.text}\n")
                    f.write("Context After:\n")
                    f.write(f"{quote.context_after}\n")
                    f.write("-" * 80 + "\n")

            logger.info(f"\nSaved {len(self.quotes)} quotes")
            logger.info(f"Full quotes with context saved to {detailed_file}")
            
        except Exception as e:
            logger.error(f"Error saving data: {str(e)}")
            raise

class QuoteDeduplicator:
    def __init__(self):
        self.seen_quotes = {}
        self.debug_info = defaultdict(list)
        
    def is_duplicate(self, quote: Quote) -> bool:
        """Determines if a quote is a duplicate."""
        quote_text = quote.text.strip()
        
        if quote_text in self.seen_quotes:
            existing_quote = self.seen_quotes[quote_text]
            
            # Same speaker and book - likely true duplicate
            if existing_quote.speaker == quote.speaker and existing_quote.book == quote.book:
                self.debug_info["exact_duplicates"].append({
                    "text": quote_text,
                    "speaker": quote.speaker,
                    "book": quote.book
                })
                return True
            
            # Different speaker, same book - could be attribution error
            if existing_quote.book == quote.book:
                if quote.confidence < existing_quote.confidence:
                    self.debug_info["lower_confidence_duplicates"].append({
                        "text": quote_text,
                        "speaker1": existing_quote.speaker,
                        "speaker2": quote.speaker,
                        "confidence1": existing_quote.confidence,
                        "confidence2": quote.confidence
                    })
                    return True
                else:
                    # Replace existing quote with higher confidence version
                    self.seen_quotes[quote_text] = quote
                    return False
            
            # Cross-book duplicate - likely legitimate repetition
            self.debug_info["cross_book_duplicates"].append({
                "text": quote_text,
                "book1": existing_quote.book,
                "book2": quote.book
            })
            return False
            
        # Not a duplicate - add to seen quotes
        self.seen_quotes[quote_text] = quote
        return False

def main():
    try:
        parser = HerodotusParser()
        parser.fetch_texts()
        combined_text = parser.clean_texts()
        parser.split_into_books(combined_text)
        parser.process_books()
        parser.save_data()
        logger.info("Processing completed successfully")

    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        sys.exit(1)
    
if __name__ == "__main__":
    main()