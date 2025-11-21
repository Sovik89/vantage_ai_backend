import spacy

# Load the small English model (make sure it's installed)
# You can install it using: python -m spacy download en_core_web_sm
nlp = spacy.load("en_core_web_sm")

# Test text
text = "Apple is looking at buying U.K. startup for $1 billion next quarter."

# Process the text
doc = nlp(text)

print("=== Tokens and Part-of-Speech Tags ===")
for token in doc:
    print(f"{token.text:<15} | POS: {token.pos_:<10} | Lemma: {token.lemma_}")

print("\n=== Named Entities ===")
for ent in doc.ents:
    print(f"{ent.text:<20} | Label: {ent.label_}")

print("\n=== Dependency Parse (who depends on whom) ===")
for token in doc:
    print(f"{token.text:<15} <-- {token.dep_:<10} -- {token.head.text}")

print("\n=== Sentence Segmentation ===")
for sent in doc.sents:
    print(f"SENTENCE: {sent.text}")
