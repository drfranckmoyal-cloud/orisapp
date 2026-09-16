# Handoff Checklist

Before first Claude Code run:
- [ ] Unzip pack into project workspace.
- [ ] Initialize git repo.
- [ ] Commit handoff pack as baseline tag `product-spec-v1.2`.
- [ ] Give Claude Code `prompts/CLAUDE_CODE_PROMPTS.md` Prompt 0 only.
- [ ] Do not paste API keys into chat or repo.
- [ ] Keep providers on `mock` through M1.
- [ ] Review first schema/migration PR before audio work.
- [ ] Connect GitHub to ChatGPT if you want independent PR/repo review here.

Before real patient data:
- [ ] production hosting architecture reviewed;
- [ ] HDS scope/contracts reviewed;
- [ ] provider retention/training/region reviewed;
- [ ] patient information workflow approved;
- [ ] PHI-safe logging verified;
- [ ] purge/backup/restore tested;
- [ ] clinical staging/evals passed.
