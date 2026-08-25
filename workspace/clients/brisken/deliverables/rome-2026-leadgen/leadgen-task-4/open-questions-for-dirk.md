# Open questions blocking a send

Ten rows carry a `send_hold` and are excluded from every motion until cleared.
Each question below resolves with one word.

## Blocking a specific person

1. **Victoria Boclinca (BSTDB).** Her row's email is `rtsompani@bstdb.org`, which
   belongs to a different person at BSTDB. Both other BSTDB rows match their
   owners, and the bad value came straight from TA Cook's export. What is her own
   address, or should she only be cc'd on Christos Georgiou's thread?
   *(`send_hold = verify_email`)*

2. **Dogan Yesil (Roche).** He is a **Cc on your H5 Roche note**, on
   `dogan.yesil1@hotmail.com`. A personal hotmail address for a bespoke note with
   an attached deck. Send there, use a Roche address, or drop the cc?
   *(`send_hold = needs_corporate_email`)*

3. **Steinar Páll Landrø (VW).** Salute as `Steinar`, or is `Steinar Páll` the
   double given name? *(`send_hold = owner_decision`)*

4. **Fabio Mora (Ferrero) and Bruno Forret (CUSP).** You ended one note with
   `=> GA` and the other with `General awareness (GA) is always good`. Confirming
   both are general-awareness holds and not warm sends? (yes / no)
   *(`send_hold = owner_decision`)*

5. **Leonid Opanasyk (DSV).** The only address he left at the booth is a personal
   gmail. Send there, wait for a corporate address, or skip?
   *(`send_hold = needs_corporate_email`)*

6. **Four people with no reachable channel:** Domenic (JTI, first name only, no
   surname on file), Isabelle Badoux (Sanofi), Adela Dolezalova (Zalando), Maria
   Moeller (Zalando). Do you have addresses, or do these rows get dropped?
   *(`send_hold = needs_enrichment`. Note: an earlier draft of this work proposed
   an address for Isabelle that exists in no source. It was rejected rather than
   guessed.)*

## Blocking a group

7. **T2 includes 17 partners and SAP staff.** You wrote "personal outreach DN" on
   13 partner/SI rows (Deloitte, KPMG, PwC, Nagarro, Zanders, LeverX, INTENSUM,
   SINVA, Target Networks, Eprox, Tradeweb) and "DN follow up on ICD Dashboard"
   on 4 SAP employees. They are classified `T2` with `lead_type = partner_si` or
   `sap_internal`, so they are visible and separable. Confirming these are
   relationship touches from you personally, and never the treasury sequence?

8. **Ashok Kumar (Accenture)** is the only SAP partner left un-stopped with a real
   email and no note. He also has a live MDH referral task on the Planner board.
   Should his row stay `DEFERRED`, or move to a named referral thread?

9. **Adela Dolezalova** exists twice: `stop = X` at Trillion Consulting, and a
   live Zalando referral from Lokesh Doggala. Pursue the Zalando side, or keep her
   excluded as an SI?

## Not blocking, but you should know

10. **`asako teruki` was emailed as "Hi asako"** on 2026-07-08, from the lowercase
    name in the sheet. Corrected now. Nothing to do, but if she replies oddly,
    that is why.

11. **Five people show live positive engagement with no follow-up recorded:**
    Christos Georgiou (BSTDB), Uffe Teisner-Kjaer (Grundfos, "call after the
    summer"), Jose Vergel (Holcim, booked), Akash Gupta (Maersk, owed docs),
    Jean-Baptiste Disdet (JTI, owed the MDH deck). These are open commitments.

12. **The booth-network draft calls four people "active customers"** (Snersrud,
    Lundemo Larsen, Haegemans, teruki) and gives them a different template. The
    CRM says none of them is a customer. The draft is being corrected, not the
    sheet. Exactly 2 rows carry `is_customer = TRUE`, both at Equinor.
