# Session Start

When beginning a new conversation where a client name is mentioned or evident from context:

1. Suggest running `/resume {client}` if not already done
2. Check for unresolved comms items (staleness > 3 days)
3. Reference the last checkpoint's `next_steps` if available
4. Begin tracking session pressure signals (see session-pressure rule)

This ensures continuity between sessions and prevents context loss.
