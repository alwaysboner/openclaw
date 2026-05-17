# SENSITIVE_PATHS.md
> Read only when task explicitly requires it. Never log values. Never echo to output.
> openclaw.json clobbered 9 times — always back up before editing.

## Credentials & Keys
| Item | Path |
|------|------|
| AWS credentials | `~/.aws/credentials` |
| AWS config | `~/.aws/config` |
| Boto config | `~/.boto` |
| GCloud ADC | `~/.config/gcloud/application_default_credentials.json` |
| GCloud tokens | `~/.config/gcloud/access_tokens.db` |
| Vertex key | `~/config/vertex-key.json` |
| GitHub CLI | `~/.config/gh/hosts.yml` |
| WhatsApp pairing | `~/.openclaw/credentials/whatsapp-pairing.json` |
| SSH private key | `~/.ssh/id_ed25519` |
| SSH authorized keys | `~/.ssh/authorized_keys` |
| TLS cert | `~/config/ip-172-26-11-178.tail7b0d0c.ts.net.crt` |
| TLS key | `~/config/ip-172-26-11-178.tail7b0d0c.ts.net.key` |

## OpenClaw Config
| Item | Path | Notes |
|------|------|-------|
| Main config | `~/.openclaw/openclaw.json` | Back up before editing |
| Last good | `~/.openclaw/openclaw.json.last-good` | Primary restore point |
| Device auth | `~/.openclaw/identity/device-auth.json` | |
| Device identity | `~/.openclaw/identity/device.json` | |
| Exec approvals | `~/.openclaw/exec-approvals.json` | |

## Rules
1. Never print values to any log or output stream.
2. Refresh from source — do not cache credential values between tool calls.
3. Config edits: back up first, verify diff, then apply. Never clobber directly.
