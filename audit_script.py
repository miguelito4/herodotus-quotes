import json
import random

def audit_quotes(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        quotes = json.load(f)
        
    croesus_cyrus_quotes = [q for q in quotes if q['speaker'] in ['Croesus', 'Cyrus']]
    
    report = []
    report.append("Data Quality Audit Report")
    report.append("=========================\n")
    
    report.append("Edge Case Analysis: Croesus & Cyrus")
    report.append("-----------------------------------")
    
    for q in croesus_cyrus_quotes:
        text = q['text']
        speaker = q['speaker']
        
        # Verification Checks
        starts_capital = text[0].isupper() if text else False
        has_said = "said:" in text
        has_answered = "answered:" in text
        
        status = "PASS"
        issues = []
        if not starts_capital:
            issues.append("Starts with lowercase")
        if has_said:
            issues.append("Contains 'said:'")
        if has_answered:
            issues.append("Contains 'answered:'")
            
        if issues:
            status = f"FAIL ({', '.join(issues)})"
            
        report.append(f"Speaker: {speaker}")
        report.append(f"Text: \"{text}\"")
        report.append(f"Verification: {status}")
        report.append("")
        
    report.append("Random Tag Check (3 Samples)")
    report.append("----------------------------")
    
    sample_quotes = random.sample(quotes, 3)
    for q in sample_quotes:
        report.append(f"Quote: \"{q['text'][:50]}...\"")
        report.append(f"Tags: {q['tags']}")
        report.append("")

    return "\n".join(report)

if __name__ == "__main__":
    print(audit_quotes('src/data/quotes.json'))
