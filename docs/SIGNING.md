# Code signing (optional, recommended)

Unsigned programs that install a global mouse hook often trigger Windows SmartScreen ("unknown publisher")
and antivirus heuristics. Signing the release exe fixes the publisher warning, lets users verify the file
came from this project, and builds SmartScreen reputation over time.

The build workflow already contains a signing step. It stays **dormant** until you switch it on.

## Option A — Azure Artifact Signing (used by the workflow)

1. Create an Artifact Signing account and a certificate profile in the Azure portal
   (check Microsoft's current eligibility rules for individual developers).
2. Create an app registration (service principal) and give it the
   **Artifact Signing Certificate Profile Signer** role on the certificate profile.
3. In the GitHub repository → *Settings → Secrets and variables → Actions*:
   - **Secrets:** `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`
   - **Variables:** `SIGNING_ENDPOINT` (e.g. `https://weu.codesigning.azure.net`), `SIGNING_ACCOUNT`,
     `SIGNING_PROFILE`, and `SIGNING_ENABLED` = `true`
4. Push a version tag. The exe is signed before its SHA-256 is computed and published.

## Option B — SignPath Foundation (free for open-source projects)

Apply at <https://signpath.org>. If accepted, replace the signing step in `.github/workflows/build.yml`
with SignPath's GitHub action as described in their onboarding instructions.

## Verify a signed release

```bat
powershell -c "Get-AuthenticodeSignature .\Misbaha.exe | Format-List"
certutil -hashfile Misbaha.exe SHA256
```

Compare the hash with `Misbaha.exe.sha256` attached to the GitHub release.
