"""Unwire each identity call site and confirm a caller-level test goes red."""
import subprocess

MOD = r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1-identity\workspace\clients\brisken\automations\expense-reconciliation"
SRC = MOD + r"\src\expense_recon"
TEST = (f'uv run --directory "{MOD}" --extra dev --extra web pytest '
        'tests/test_merchant_identity_216.py -q -p no:cacheprovider')
CASES = [
    ("recall keys on the identity", SRC + r"\learning\consult.py",
     "ikey = self.identity.key(vendor) or vnorm", "ikey = vnorm"),
    ("categorize hands memory the registry identity", SRC + r"\categorize.py",
     "learned = learned.with_identity(MerchantIdentityResolver(registry))", "learned = learned"),
    ("registry probes the identity", SRC + r"\merchant_registry.py",
     "identity_key(vendor_clean), identity_key(vendor_raw),", ""),
    ("capture keys on the identity", SRC + r"\learning\capture.py",
     "vnorm = identity_key(r.detected_vendor)", "vnorm = normalize_vendor(r.detected_vendor)"),
    ("_registry_account asks about the matched merchant", SRC + r"\categorize.py",
     "recall = _recall_for(receipt, learned, match)", "recall = _recall_for(receipt, learned)"),
]
for name, f, old, new in CASES:
    p = subprocess.run(
        ["uv", "run", r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1\tools\regress_check.py",
         "--test", TEST, "--file", f, "--replace", old, "--with", new],
        capture_output=True, text=True, cwd=MOD)
    tail = [ln for ln in (p.stdout + p.stderr).splitlines() if ln.strip()][-4:]
    print(f"== {name}: exit {p.returncode}")
    for ln in tail:
        print("   ", ln[:200])
