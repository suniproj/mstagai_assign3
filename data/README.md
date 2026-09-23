# Agent 2 Challenge Dataset

15 intentionally messy synthetic recipes plus 15 golden validation cases.

The set includes clear PASS, clear FAIL, semantic FAIL, and NEEDS_REVIEW examples.
It stays separate from the Assignment 2 Pinecone corpus and is used to develop/evaluate
Agent 2 before changing the production recipe knowledge base.

Agent 2 should use deterministic checks for explicit evidence, semantic reasoning for
ingredient relationships, and NEEDS_REVIEW when evidence is genuinely ambiguous.
