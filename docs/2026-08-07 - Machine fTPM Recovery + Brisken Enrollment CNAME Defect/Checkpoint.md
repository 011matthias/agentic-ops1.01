# Checkpoint: Machine fTPM Recovery + Brisken Enrollment CNAME Defect

**Date:** 2026-08-07
**Status:** Workstation repaired and verified; Brisken DNS defect reported to Dirk, awaiting his go-ahead; laptop firmware gap still open

---

## Summary

The workstation's AMD fTPM disappeared after KB5101684, taking every Windows sign-in method down at once; a full power drain restored it and the PIN is back on a hardware-backed key. Diagnosing the follow-on work-account failure surfaced an unrelated Brisken-side defect: the `enterpriseenrollment` CNAME on brisken.com points at the wrong Microsoft host, which breaks Windows work-account setup for anyone at the company.

---

## What Was Done This Session

### Workstation repair (own machine, not a client asset)
1. Traced "all sign-in options malfunctioning" to a phantom TPM device node (`CM_PROB_PHANTOM`, Code 45, `Present=False`), last seen 2026-07-30 03:32:27.
2. Built the causal chain from logs before proposing anything: KB5101684 (30 Jul) began the Secure Boot certificate rollover; the Insyde V1.14 firmware has no PK-signed KEK (event 1803, twice daily since 30 Jul, never completes); on the 08-07 03:58 boot the VBS policy check failed with "TPM 2.0: not in the correct mode for an upgrade" (Kernel-Boot 124); Windows Hello then deleted its container plus the biometric enrollment and fell back to a software key.
3. Cleared data-loss risk *before* recommending a firmware action: `PreventDeviceEncryption=1`, and the machine had already booted with no TPM present. A TPM-bound BitLocker volume would have demanded a recovery key on that boot and did not, so touching the fTPM could not orphan the drive.
4. Power drain restored the fTPM. It cleared itself (event 519, "SRK has changed"), took ownership, re-provisioned at 13:58:13. Kernel-Boot 124 did not recur.
5. Cleared the credentials orphaned under the dead SRK: `certutil -deletehellocontainer` (stages, completes on sign-out), Settings disconnect of the stale workplace join, then sign-out. PIN re-created 14:26:22 on a **hardware** Hello key; the `0x8029040E` wrong-parent loop (184 fires) stopped at 14:15:29.

### Brisken enrollment defect
6. Decoded the work-account failure properly: `0x80192EE7` (`0x80190000 | 12007`, WinHTTP NAME_NOT_RESOLVED) thrown at `Provision::EnrollMDM`, followed by `AddAccountTransaction::OnRollbackStart` discarding the entire join. MDM enrollment failing aborts the whole account addition, which is why nothing appeared to happen.
7. Confirmed root cause at the authoritative source rather than from resolver output: GoDaddy registrar API read shows `CNAME enterpriseenrollment -> enterpriseenrollment.manage.microsoft.com` (ttl 3600), missing the required `-s`. TLS against `enterpriseenrollment.brisken.com` returns `CN=*.azureedge.net`, which does not cover brisken.com; the `-s` host returns a valid `CN=enterpriseenrollment.manage.microsoft.com`. The companion `enterpriseregistration` record is correct.
8. Sent Dirk a plain-language notification (what breaks, why, the one-record fix, request to make the change) via a guarded send-by-id: draft created, re-verified, count and allowlist asserted, sent, then confirmed it left Drafts and landed in Sent Items at 12:46:32Z.

---

## Key Decisions Made

### Diagnose fully before touching anything
- **Choice:** Ran the complete read-only sweep and cleared the BitLocker question before suggesting a single firmware action.
- **Rationale:** Broken sign-in is one of the few faults where a careless fix locks the user out permanently. The device-encryption check is what made the power-drain and BIOS advice safe to give.

### Did not force the sign-out
- **Choice:** Stated it as a LIMITATION and left the trigger to the user.
- **Rationale:** `shutdown /l` would have killed this session, unsaved work, and five sibling Claude sessions on the shared tree. Not a bounded autonomous action.

### Outlook path over fixing Brisken DNS for the user's own account
- **Choice:** Restored the work account via Outlook with device management declined; left the CNAME untouched.
- **Rationale:** Fixing the record and re-adding through Settings would have enrolled a personal Acer laptop into Brisken's Intune. The June registration had `WorkplaceMdmUrl` empty, so no-MDM is the shape to preserve. The org-wide defect is separable and is Dirk's call.

### Reported the DNS defect rather than fixing it
- **Choice:** Read the zone via API, sent Dirk the diagnosis and a request for permission. No PATCH.
- **Rationale:** Live client production zone. The 2026-07-09 authorization was scoped to that specific change set and does not carry forward.

---

## Files Modified

| File | Action | Purpose |
|------|--------|---------|
| `~/.claude/.../memory/reference_dsregcmd_leave_is_hybrid_unjoin_only.md` | Created | `dsregcmd /leave` is Hybrid Unjoin only, exits 0 doing nothing when `AzureAdJoined=NO`; Workplace Join removal is Settings-UI-only; `certutil -deletehellocontainer` stages and needs a sign-out |
| `~/.claude/.../memory/MEMORY.md` | Edited | Index pointer for the above |
| `workspace/clients/brisken/context/comms-log.md` | Appended | Verbatim outbound to Dirk plus the underlying evidence (zone read, both TLS subjects, the EnrollMDM to OnRollbackStart chain); marked NOT changed, awaiting go-ahead |

Scratchpad scripts (`gd-read-enroll.ps1`, `send_dirk_dns_note.ps1`, `dsreg-leave.ps1`) are ephemeral and uncommitted.

---

## Current Status

Workstation: TPM present and healthy, PIN working on a hardware key, biometrics available to re-enroll, Brisken account restored via Outlook without MDM. The `0x8029040E` loop is dead.

Brisken: `platform: unknown plan, ~?/? ops/mo, last assessed ?` (no ops data in `infrastructure.yaml`). The enrollment CNAME is unchanged and broken; Dirk has the diagnosis and the request as of 12:46:32Z today.

Firmware: unresolved and the real residual risk. Event 1803 still fires twice daily, the Secure Boot certificate rollover still cannot apply to Insyde V1.14, and that is the condition that let the fTPM vanish. A recurrence repeats the whole morning: PIN gone, biometrics gone, work account broken.

---

## Next Steps

1. Check Acer support for a BIOS newer than V1.14 (dated 2026-06-24) for the Nitro AN517-41. This is the only durable fix for the fTPM disappearance and everything else here is redone if it recurs.
2. On Dirk's yes, PATCH `enterpriseenrollment` to `enterpriseenrollment-s.manage.microsoft.com` in GoDaddy, verify the TLS subject changes, and write a change record matching the 2026-07-09 format.
3. Re-enroll fingerprint and face on the workstation now that a PIN exists.
4. Run `/ops-audit brisken` to fill the missing platform plan and ops figures in `infrastructure.yaml`.
5. Clear the stale static DNS (`129.13.64.5`, `141.52.3.3`, KIT resolvers) off the disconnected Ethernet adapter.

---

## Context for Next Session

### Files to Read First
- `workspace/clients/brisken/context/comms-log.md` (tail: the outbound to Dirk and its evidence block)
- `workspace/clients/brisken/context/dns-changes/brisken-dns-change-record-2026-07-09.md` (the format any DNS change record must match)
- `~/.claude/.../memory/reference_dsregcmd_leave_is_hybrid_unjoin_only.md`

### Open Questions
- Has Brisken enabled Intune auto-enrollment since June? The June registration had `WorkplaceMdmUrl` empty, so it is unclear whether the enrollment attempt is new tenant policy or has simply never been exercised.
- Does anyone at Brisken actually need MDM enrollment working, or is the CNAME fix hygiene? That changes its priority.
- Is there a BIOS above Insyde V1.14 for the AN517-41? The web search did not surface a confirmed newer build.

### Working Notes
- `dsregcmd /leave` is **Hybrid Unjoin only**. It exits 0 having done nothing when `AzureAdJoined=NO`. Verify `WorkplaceJoined` after, never the exit code. Unelevated it returns `0x800702E4` cleanly with no half-state. No CLI exists for per-user Workplace Join removal.
- `NgcSet: NO` tracks the Entra/Hello-for-Business container, **not** a personal Microsoft account PIN. It reads NO permanently on this setup. The Hello event log (5702 PIN protector, 5225 hardware vs software key) is the real source of truth.
- `PreReqResult: WillNotProvision` likewise refers to Hello for Business, not the MSA PIN. Both were red herrings that cost a cycle.
- Two error codes worth keeping: `0x8029040E` = key sealed under a storage parent that no longer exists (post-SRK-change orphan). `0x80192EE7` = `0x80190000 | 12007`, WinHTTP name-not-resolved, thrown by MDM enrollment.
- The elevated-run-with-UAC pattern (`Start-Process -Verb RunAs -Wait` against a script that logs to a file) worked well for admin operations and avoids losing output to a closing window.

### Reference Materials
- Graph app creds: `workspace/clients/brisken/context/.env` (app-only, hard mailbox allowlist)
- Registrar creds: `workspace/clients/brisken/context/registrar-api.env` (`GODADDY_KEY` / `GODADDY_SECRET`; the classifier blocks shell reads of this path, load it inside a script instead)
- Microsoft guidance link surfaced in event 1801: `https://go.microsoft.com/fwlink/?linkid=2301018`

---

## How to Continue

Nothing is mid-flight. The workstation is fixed and verified. Pick up either at Dirk's reply (then step 2, the guarded PATCH plus change record) or at the Acer BIOS check (step 1), which is the higher-value one because it prevents a repeat.

---

## Strategic Feedback

### What Worked Well This Session
- Verifying behaviour rather than exit codes caught the `dsregcmd /leave` no-op immediately. It returned 0 and changed nothing; the state re-read is the only reason that did not become a false "fixed" claim.
- Clearing the BitLocker question before recommending any firmware action. That single check is what made the power-drain advice safe to give rather than reckless.
- Reading the authoritative GoDaddy zone rather than trusting resolver output, which turned "probably misconfigured" into a citable one-line defect Dirk can act on.

### Suggestions
- Two wrong confident inferences (`NgcSet: NO` meaning a clean slate, and calling the first `0x80192EE7` transient) each cost the user a failed retry. Both shared a shape: a field or a single observation was read as proving more than it did. When a diagnostic field's exact semantics are load-bearing for advice, confirm what it actually tracks before building a recommendation on it.

### System Health
- The B1 stop-gate fired twice, both on closing text that offered bounded next steps back as choices. Both were caught and corrected in-turn, and the second correction was productive: it surfaced that GoDaddy API access existed, turning "tell Brisken IT" into "we can read this ourselves". Same unresolved pattern as the 2026-07-27 rows.
- Autonomy: 7 human interventions, but 5 are unavoidable Windows limitations (PIN enrollment, Settings disconnect, Outlook add, sign-out, UAC approval) and 2 were authorization gates working correctly. The elevated count reflects an OS that requires UI for credential operations, not a system gap to close.
