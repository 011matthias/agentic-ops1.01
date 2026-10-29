# {Client} tests

Offline tests against committed fixtures. CI runs them with no tenant credential and never calls n8n or the client's other systems; a test that needs live data skips when its snapshot is absent.

Fixtures carry placeholder values only: no real names, addresses, IDs or keys.
