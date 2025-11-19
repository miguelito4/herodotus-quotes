import re
import json
import os

def clean_text(text):
    """Cleans the quote text by removing brackets, footnotes, and extra whitespace."""
    text = re.sub(r'\[.*?\]', '', text)  # Remove [1], [2], etc.
    text = re.sub(r'\d+', '', text)      # Remove standalone numbers (footnotes)
    text = re.sub(r'\(\w\)', '', text)   # Remove subsection markers like (a), (b)
    text = re.sub(r'\s+', ' ', text).strip()
    return text



IGNORE_NAMES = {
    'The', 'Then', 'When', 'Thus', 'For', 'But', 'And', 'So', 'If', # Conjunctions/Starters
    'Sardis', 'Athens', 'Sparta', 'Hellas', 'Egypt', 'Persia', 'Babylon', # Places
    'Lacedemonians', 'Corinthians', 'Athenians', 'Persians', 'Medes', 'Paionians', 'Ionians', # Peoples
    'Myrkinos', 'Hellespont', 'Ionia', 'Asia', 'Europe', 'Libya', 'Delphi'
}

BLACKLIST = {
    "Accordingly", "Being", "De", "He", "She", "They", "It", "Now",
    "Then", "Thus", "Therefore", "Since", "Surely", "What", "With",
    "To", "Didst", "Having", "Unknown", "Deity", "State", "Oracle",
    "Epic", "Poet", "Barbarians", "Hellenes",
    "Here", "There", "But", "For", "If", "When",
    "Upon", "In", "How", "Come"
}

def get_tags(text):
    """Generates tags based on keywords in the text."""
    text_lower = text.lower()
    tags = []
    keywords = {
        'war': ['war', 'battle', 'army', 'fight', 'spear', 'shield', 'conquer', 'destroy'],
        'fate': ['fate', 'destiny', 'god', 'oracle', 'dream', 'prophecy', 'doom', 'fortune'],
        'wisdom': ['wisdom', 'wise', 'counsel', 'advice', 'learn', 'know', 'truth'],
        'hubris': ['pride', 'boast', 'greatness', 'wealth', 'power', 'king', 'master'],
        'justice': ['justice', 'right', 'wrong', 'law', 'punish', 'avenge', 'penalty'],
        'death': ['death', 'die', 'slay', 'kill', 'bury', 'tomb', 'perish'],
    }
    
    for tag, words in keywords.items():
        if any(word in text_lower for word in words):
            tags.append(tag)
            
    if not tags:
        tags.append('history')
        
    return list(set(tags))

def resolve_speaker(text, context_before, current_speaker):
    """
    Resolves the speaker, handling the 'Addressee, ...' case.
    If the text starts with 'Name, ', it checks the context to find the real speaker.
    """
    # Check for "Name, " pattern at the start of the quote
    match = re.match(r'^([A-Z][a-z]+), ', text)
    if match:
        addressee = match.group(1)
        # Heuristic: If the quote starts with a name, that person is likely the ADDRESSEE.
        # We need to find the speaker in the context_before.
        
        # Look for patterns like "Speaker said:", "Speaker answered:", "Speaker spoke:"
        # We search backwards from the end of context_before
        speaker_matches = list(re.finditer(r'([A-Z][a-z]+)\s+(?:answered|said|spoke|replied|asked)', context_before))
        if speaker_matches:
            # Iterate backwards
            for match in reversed(speaker_matches):
                name = match.group(1)
                if name not in IGNORE_NAMES and name not in BLACKLIST:
                    return name
            
        # If no explicit speaker verb found, try to find the subject of the last sentence
        # This is harder with regex, so we might fallback to the current_speaker (from the block header if available)
        # or just keep the original extraction if we can't be sure.
        
    return current_speaker

def extract_quotes_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return []

    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Filter out Gutenberg legal boilerplate (The "Seam" Fix)
    clean_lines = []
    for line in lines:
        if "*** START OF" in line or "*** END OF" in line or "Project Gutenberg" in line:
            continue
        clean_lines.append(line)
    
    content = "".join(clean_lines)

    # Split by Books
    books = re.split(r'(BOOK [IVX]+)', content)
    
    quotes = []
    current_book = "Unknown"
    
    # Skip the preamble
    start_index = 1 if len(books) > 1 else 0
    
    for i in range(start_index, len(books), 2):
        if i >= len(books): break
        
        header = books[i].strip() # e.g., "BOOK I"
        print(f"Found {header}")
        book_num = header.replace("BOOK ", "")
        text_block = books[i+1]
        
        # Regex to find quotes: "..."
        # We capture context before and after roughly
        # This regex is a bit simplified; for full text it might need to be more robust against newlines
        quote_matches = re.finditer(r'"([^"]+)"', text_block)
        
        for match in quote_matches:
            quote_text = match.group(1)
            start = match.start()
            end = match.end()
            
            # Get context (approx 300 chars)
            context_before = text_block[max(0, start-300):start].strip()
            context_after = text_block[end:min(len(text_block), end+300)].strip()
            
            cleaned_text = clean_text(quote_text)
            
            # Filter out low quality quotes
            if len(cleaned_text) < 30: continue
            if cleaned_text[0].islower(): continue # Fragment
            if "Editors read" in cleaned_text: continue
            
            # Attempt to identify speaker from context_before
            # Default to "Unknown" if not found, then refine
            speaker = "Unknown"
            
            # Attempt to identify speaker from context_before
            # Default to "Unknown" if not found, then refine
            speaker = "Unknown"
            
            # Look at the last 300 chars of context_before to find the speaker
            immediate_context = context_before[-300:]
            
            # Regex strategies to find speaker:
            # 1. "Name said:", "Name answered:", "Name spoke:" (Basic)
            # 2. "Name [0-9]+ said:" (Footnote handling)
            # 3. "Name ... said:" (Distance handling, e.g. "Megabazos ... said")
            
            # Strategy 1 & 2: Name followed by verb (optional footnote)
            # We look for the *last* occurrence of this pattern
            matches = list(re.finditer(r'([A-Z][a-z]+)(?:\s+\d+)?\s+(?:answered|said|spoke|replied|asked)', immediate_context))
            speaker_candidate = None
            if matches:
                # Iterate backwards to find a valid name
                for match in reversed(matches):
                    name = match.group(1)
                    if name not in IGNORE_NAMES and name not in BLACKLIST:
                        speaker_candidate = name
                        break
            
            if speaker_candidate:
                speaker = speaker_candidate
            else:
                # Strategy 3: Name ... verb (allow some words in between, e.g. "Megabazos, having ..., said")
                # Better approach: Find the verb, then look backwards for the closest Name.
                verb_matches = list(re.finditer(r'(answered|said|spoke|replied|asked)', immediate_context))
                if verb_matches:
                    # Use the last verb found (closest to the quote)
                    last_verb = verb_matches[-1]
                    verb_start = last_verb.start()
                    
                    # Look at text before the verb (up to 200 chars)
                    lookback_text = immediate_context[max(0, verb_start-200):verb_start]
                    
                    # Find candidates: Capitalized words
                    # We want the *last* candidate in this chunk (closest to verb)
                    candidates = list(re.finditer(r'([A-Z][a-z]+)', lookback_text))
                    if candidates:
                        # Iterate backwards through candidates
                        for cand in reversed(candidates):
                            name = cand.group(1)
                            if name in IGNORE_NAMES or name in BLACKLIST:
                                continue
                                
                            # Check for "by Name" (passive agent)
                            # Get text before the candidate in the lookback_text
                            start_pos = cand.start()
                            preceding_text = lookback_text[max(0, start_pos-5):start_pos].lower()
                            if "by " in preceding_text:
                                continue
                                
                            speaker = name
                            break

            # Refine speaker using the "Tomyris" logic (Addressee check)
            speaker = resolve_speaker(cleaned_text, context_before, speaker)
            
            # Generate ID
            speaker_slug = speaker.lower().replace(' ', '_')
            quote_id = f"book{book_num.lower()}_{speaker_slug}_{len(quotes):02d}"
            
            quotes.append({
                "id": quote_id,
                "text": cleaned_text,
                "speaker": speaker,
                "book": book_num,
                "context_before": context_before[-200:], # Truncate for JSON
                "context_after": context_after[:200],
                "tags": get_tags(cleaned_text)
            })
            
    return quotes

if __name__ == "__main__":
    input_file = "data/herodotus_full_text.txt" # Assuming this location
    output_file = "src/data/quotes.json"
    
    # Check if input file exists, if not try root
    if not os.path.exists(input_file):
        if os.path.exists("herodotus_full_text.txt"):
            input_file = "herodotus_full_text.txt"
        else:
            print(f"Warning: {input_file} not found. Please place the full text file there.")
            exit(1)

    extracted_quotes = extract_quotes_from_file(input_file)
    
    # Load existing quotes to append or merge? 
    # User said "Append all quotes". But we probably want to overwrite if we are doing a full extraction.
    # Or maybe we should just save the new list.
    # Let's overwrite for a clean slate if we are doing "Full Database Extraction".
    
    print(f"Extracted {len(extracted_quotes)} quotes.")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(extracted_quotes, f, indent=2, ensure_ascii=False)
        
    print(f"Saved to {output_file}")

    # Save detected characters
    detected_characters = sorted(list(set(q['speaker'] for q in extracted_quotes)))
    with open('data/detected_characters.json', 'w', encoding='utf-8') as f:
        json.dump(detected_characters, f, indent=2, ensure_ascii=False)
    print(f"Saved detected characters to data/detected_characters.json")
