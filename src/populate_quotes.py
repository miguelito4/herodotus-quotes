import json
import re
import random

def parse_quotes_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by separator
    blocks = content.split('--------------------------------------------------------------------------------')
    quotes = []
    
    for block in blocks:
        if not block.strip():
            continue
            
        quote_data = {}
        lines = block.strip().split('\n')
        
        current_field = None
        buffer = []
        
        for line in lines:
            if line.startswith('Speaker: '):
                if current_field:
                    quote_data[current_field] = '\n'.join(buffer).strip()
                quote_data['speaker'] = line.replace('Speaker: ', '').strip()
                current_field = None
                buffer = []
            elif line.startswith('Book: '):
                quote_data['book'] = line.replace('Book: ', '').strip()
            elif line.startswith('Quote:'):
                if current_field:
                    quote_data[current_field] = '\n'.join(buffer).strip()
                current_field = 'text'
                buffer = []
            elif line.startswith('Context Before:'):
                if current_field:
                    quote_data[current_field] = '\n'.join(buffer).strip()
                current_field = 'context_before'
                buffer = []
            elif line.startswith('Context After:'):
                if current_field:
                    quote_data[current_field] = '\n'.join(buffer).strip()
                current_field = 'context_after'
                buffer = []
            elif line.startswith('Pattern:') or line.startswith('Confidence:'):
                continue
            else:
                if current_field:
                    buffer.append(line)
        
        if current_field:
            quote_data[current_field] = '\n'.join(buffer).strip()
            
        if 'text' in quote_data and 'book' in quote_data:
            quotes.append(quote_data)
            
    return quotes

def clean_text(text):
    if not text:
        return ""
    # Remove [ ] and contents if they are footnotes like [1]
    text = re.sub(r'\[.*?\]', '', text)
    # Remove standalone numbers often used as footnotes in this text
    text = re.sub(r'\s\d+\s', ' ', text)
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_tags(text, speaker):
    tags = []
    text_lower = text.lower()
    
    keywords = {
        'war': ['war', 'battle', 'army', 'fight', 'spear', 'shield', 'conquer'],
        'fate': ['fate', 'destiny', 'gods', 'oracle', 'divine', 'doom', 'fortune'],
        'wisdom': ['wisdom', 'wise', 'counsel', 'advice', 'learn', 'know'],
        'hubris': ['pride', 'insolence', 'wealth', 'mighty', 'king', 'power'],
        'justice': ['justice', 'law', 'right', 'wrong', 'punish', 'vengeance'],
        'death': ['death', 'die', 'slay', 'kill', 'bury', 'tomb']
    }
    
    for tag, words in keywords.items():
        if any(w in text_lower for w in words):
            tags.append(tag)
            
    if not tags:
        tags.append('history')
        
    return list(set(tags))

def main():
    raw_quotes = parse_quotes_file('data/quotes_with_context.txt')
    
    # Filter for Book I and II
    target_quotes = [q for q in raw_quotes if q.get('book') in ['I', 'II']]
    
    # Select high quality ones
    quality_quotes = []
    for q in target_quotes:
        text = q.get('text', '').strip()
        
        # Skip if text is empty
        if not text:
            continue
            
        # Skip if text ends with a colon (usually narration introducing a quote)
        if text.endswith(':'):
            continue
            
        # Skip if text looks like an editor's note or garbage
        if 'Editors read' in text or 'MSS.' in text:
            continue
            
        # Skip if text is too short (likely fragments)
        if len(text) < 30:
            continue
            
        # Skip if text starts with lowercase (likely continuation/fragment)
        if text[0].islower():
            continue

        # Skip if text is just narration (heuristic: starts with "He", "She", "They" and no quotes inside, though this is risky)
        # Better heuristic: check if it's a known bad pattern
        if text.startswith("He thus inquired"):
            continue

        quality_quotes.append(q)
    
    # Prefer longer quotes but not massive ones
    # Sort by length to get "meaty" quotes, then shuffle or pick top
    # Let's just pick the ones with good length
    ideal_quotes = [q for q in quality_quotes if 50 < len(q.get('text', '')) < 600]
    
    # If we don't have enough, fall back to all quality quotes
    if len(ideal_quotes) < 50:
        selected_quotes = quality_quotes[:50]
    else:
        selected_quotes = ideal_quotes[:50]
    
    final_quotes = []
    speaker_counts = {}
    
    for q in selected_quotes:
        clean_q_text = clean_text(q.get('text', ''))
        clean_context_before = clean_text(q.get('context_before', ''))
        clean_context_after = clean_text(q.get('context_after', ''))
        
        speaker = q.get('speaker', 'Unknown')
        book = q.get('book', 'I')
        
        # Generate ID
        speaker_slug = speaker.lower().replace(' ', '_')
        count = speaker_counts.get(speaker_slug, 0) + 1
        speaker_counts[speaker_slug] = count
        quote_id = f"book{book.lower()}_{speaker_slug}_{count:02d}"
        
        final_quotes.append({
            "id": quote_id,
            "text": clean_q_text,
            "speaker": speaker,
            "book": book,
            "context_before": clean_context_before,
            "context_after": clean_context_after,
            "tags": get_tags(clean_q_text, speaker)
        })
        
    # Manual fixes for known attribution errors
    for q in final_quotes:
        # Fix Atys attributed to Croesus
        if "My father, in times past the fairest" in q['text']:
            q['speaker'] = "Atys"
            # Regenerate ID
            q['id'] = q['id'].replace('croesus', 'atys')
            
        # Fix Astyages attributed to Artembares
        if "By what death, Harpagos" in q['text']:
            q['speaker'] = "Astyages"
            q['id'] = q['id'].replace('artembares', 'astyages')
            
        # Fix Harpagos attributed to Astyages
        if "Son of Cambyses, over thee the gods keep guard" in q['text']:
            q['speaker'] = "Harpagos"
            q['id'] = q['id'].replace('astyages', 'harpagos')

        # Fix Tomyris attributed to Cyrus (Addressee confusion)
        if "Cyrus, insatiable of blood" in q['text']:
            q['speaker'] = "Tomyris"
            q['id'] = q['id'].replace('cyrus', 'tomyris')

    with open('src/data/quotes.json', 'w', encoding='utf-8') as f:
        json.dump(final_quotes, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully wrote {len(final_quotes)} quotes to src/data/quotes.json")

if __name__ == "__main__":
    main()
