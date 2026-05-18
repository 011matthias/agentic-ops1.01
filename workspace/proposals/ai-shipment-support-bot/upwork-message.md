Hi there,

Short Loom walkthrough where I break down the build: https://www.loom.com/share/2c6cd58f7180477487efd370b8ec4f4d

Quick version: you want an AI bot that answers "Where is my shipment?" and the tracking correction follow-ups, in German, across your email and the Amazon Message Center, using your existing ERP for the tracking data. That is exactly the kind of system I build.

The one design decision that matters here: the model never invents a tracking number. It handles the judgment, which order this is, what the customer is asking, how to phrase the German reply, and your ERP supplies every fact, inserted word for word. If the ERP has no answer, it hands off to a person instead of guessing.

The full build plan is on a short site if you want the detail: architecture, timeline, pricing, and a downloadable workflow skeleton.

https://unpauseai.com/clients/ai-shipment-support-bot/
Access code: ai-shipment-support-bot-2026

Happy to jump on a quick call if it is easier to talk it through.

Wenn es Ihnen lieber ist, können wir das Ganze natürlich auch komplett auf Deutsch besprechen, ganz wie Sie möchten.

Cheers,
Matthias
UnpauseAI
