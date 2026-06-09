# VolaByg Lead Flow and Deliverability: Loom Walkthrough Script

Proposer: Matthias. Target length: 2.5 to 3 minutes. Record over the proposal site.

---

### Opening

SAY: Hi there, Matthias here.
SAY: I read your message a couple of times, and before I say a word about pricing, I want to show you that the spam problem is mostly solvable already, because I can see the cause from the outside.

---

### BEAT 1: The Real Problem (Reframe)

SAY: Ibrahim, you framed this as a deliverability and tracking worry, and that instinct is right. Here is the reframe: this is not random spam, it is two things stacked.
SAY: First, warm leads are going through a cold-outreach tool. Instantly is built to email strangers at scale, but your leads just opted in on a Facebook ad seconds earlier, so they are warm. Warm mail through cold infrastructure is one of the most common reasons good email gets filtered.
SAY: Second, your Facebook lead count not matching your replies tells me leads are also being lost in the handoff, before they ever get an email. So part of the gap is spam, and part of it is leads quietly dropping. Those are two different fixes.

---

### Authority

SAY: Quickly, why me. I run this exact setup in production for another client right now: Instantly sequencing, mailbox health, and SPF, DKIM and DMARC, the email authentication records that prove a message really came from your domain.
SAY: I am based in the EU on the same timezone as Denmark, and I treat your leads as the personal data they are.

---

### BEAT 2: What I Already Found (Demo)

>> Screen: the proposal overview page, scroll down to the DNS records block
SAY: This is a public lookup of volabyg.dk. Anyone can read these records, I did not log into anything of yours to get them.
SAY: Your domain says only one provider may send mail, and your policy says reject anything that fails that check. On your main mailbox, that is good security. But if Instantly is sending as your domain, every one of those emails fails and gets rejected, which is a one-way ticket to the spam folder.
>> Click "Solution" in top nav
SAY: So the core recommendation is simple. Send warm leads from your own authenticated domain through proper transactional infrastructure, and keep your three emails on exactly the same day zero, day two, day four to five timing.

---

### BEAT 3: The Flow, the Plan, the Price

>> Click "Workflow" in top nav
>> Scroll to "Where Leads Drop"
SAY: On the workflow page I trace your current flow stage by stage and mark exactly where leads go missing today, then I put the rebuilt flow right next to it, with every handoff logged so the counts finally agree.
>> Click "Timeline" in top nav
SAY: The timeline is short. Week one is a full audit with written findings. Weeks two and three are the rebuild, verified with your real leads, not a demo. Then optional monthly management.
>> Click "Investment" in top nav
SAY: Pricing is audit-first on purpose. You start with a small fixed audit, you see precisely what is wrong, and only then do you decide on the rebuild. No big commitment before you have the findings.

---

### Close

SAY: So yes, I can take this A to Z, with one owner for the whole flow. The access code for the full site is in my message.
SAY: If it looks right, the cleanest next step is the phase one audit. Either way, thanks for the clear brief, Ibrahim, and I am happy to jump on a quick call if that is easier.

---

## LOOM NOTES VERSION

- Hi there, Matthias here. Before pricing, show the cause is already visible from outside.
- Reframe: not random spam. Warm leads on a cold tool, plus a leaky handoff. Two separate fixes.
- Authority: I run this stack in production (Instantly, SPF/DKIM/DMARC). EU, same timezone as Denmark.
- Overview DNS block: public lookup of volabyg.dk. Domain locked to one sender, reject policy, so Instantly mail fails auth.
- Solution: send warm leads from an authenticated domain, keep the three-email cadence.
- Workflow: trace current flow, mark where leads drop, show rebuilt flow with logging.
- Timeline: week 1 audit, weeks 2 to 3 rebuild verified with real leads, then monthly.
- Investment: audit-first. Small fixed audit, then decide on the rebuild.
- Close: A to Z, one owner. Access code in the message. Suggest phase 1 audit. Offer a call.
