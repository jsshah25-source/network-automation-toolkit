# Architecture

```mermaid
flowchart LR
    subgraph Sources
        M[Meraki Dashboard API v1]
        S[Sample JSON<br/>offline mode]
        C[IOS / IOS-XE<br/>config files]
    end

    subgraph netauto
        MC[meraki_client.py<br/>read-only, 429 retry]
        INV[inventory.py<br/>join, health, firmware drift]
        COMP[compliance.py<br/>baseline rules, scoring]
        CLI[cli.py]
    end

    subgraph Outputs
        HR[Health report<br/>Markdown / CSV]
        CR[Compliance report<br/>Markdown]
        GATE[CI gate<br/>exit 1 on high severity]
    end

    M --> MC
    S --> MC
    MC --> INV --> CLI
    C --> COMP --> CLI
    CLI --> HR
    CLI --> CR
    CLI --> GATE
```

## Delivery pipeline

```mermaid
flowchart LR
    DEV[Commit or pull request] --> LINT[ruff lint]
    LINT --> TEST[pytest + coverage<br/>Python 3.10 and 3.12]
    TEST --> REPORTS[Generate reports<br/>run summary + artifacts]
    DEV --> CODEQL[CodeQL scan]
    DEV --> SECRETS[Secret scanning<br/>push protection]
    DEPS[Dependabot weekly] --> DEV
```

## Design choices

- **Read-only by design.** The Meraki client only issues GET requests, so it is safe to point at production.
- **Offline client with the same interface.** Tests, demos and CI run with no API key and no network access.
- **Rules as small functions.** Each compliance rule is one line that a network engineer can read and extend.
- **Reports in Markdown.** They render in GitHub, pull requests, the Actions run summary and chat tools without extra tooling.
