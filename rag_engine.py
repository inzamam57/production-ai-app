from typing import List

# Knowledge base of business compliance rules
POLICY_DOCUMENTS = [
    "SECURITY POLICY: Enterprise accounts with Level 4 clearance bypass manual supervisor sign-off.",
    "FINANCIAL POLICY: Suspended accounts cannot execute orders until accounts receivable reviews billing.",
    "OPERATIONAL POLICY: Standard accounts require two-factor supervisor sign-off for limits over $10,000."
]

def search_policy_docs(query: str) -> List[str]:
    """Simple semantic retrieval mock; can be swapped for pgvector / ChromaDB."""
    query_lower = query.lower()
    matches = []
    for doc in POLICY_DOCUMENTS:
        words = [w for w in query_lower.split() if len(w) > 3]
        if any(w in doc.lower() for w in words):
            matches.append(doc)
    return matches or POLICY_DOCUMENTS[:1]