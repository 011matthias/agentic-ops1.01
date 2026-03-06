# Client Communication Profile Setup

Ask the user these questions to create a comms profile for a new client. Use the answers to populate `templates/comms-profile-template.md`.

## Questions

### 1. Platform
"What platform do you communicate with this client on?"
Options: Upwork, Email, Slack, WhatsApp, Other

### 2. Contacts
"Who are the key contacts? For each, I need:"
- Name
- Role (decision-maker, ops, developer, etc.)
- How technical are they? (non-technical, moderate, technical)

### 3. Formality
"How formal is your communication with this client?"
- Casual (first-name basis, contractions, chat-like)
- Professional (friendly but structured)
- Formal (business-like, polished)

### 4. Sign-Off
"How do you typically sign off messages to this client?"
Examples: "Cheers", "Thanks", "Best", or nothing (for chat platforms)

### 5. Voice
"Do you write as 'I' (solo freelancer) or 'we' (team/agency)?"

### 6. Length Preference
"How long are your typical messages to this client?"
- Short (~100 words, quick updates)
- Medium (~250 words, standard updates)
- Long (~500 words, detailed reports)

### 7. Imperfections
"How human should the messages feel?"
- Light (1 subtle natural imperfection per message — recommended)
- Off (clean and polished, no deliberate imperfections)
- Moderate (2-3 imperfections, very casual feel)

## After Collecting Answers

1. Populate the comms-profile-template.md with the answers
2. Write to `workspace/clients/{client}/context/comms-profile.md`
3. Confirm to the user what was created

## Notes

- If the user already has `context/process-notes.md` for this client, pre-fill contact info from there instead of asking again
- Default to `light` imperfections if the user doesn't have a strong preference
- For Upwork, default formality to `casual` unless told otherwise
