---
description: Check skill routing health and analytics
---

# Skill Health Check

1. Check routing analytics (Groove outcomes):
```bash
synapse --stats
```

2. Verify skills index integrity:
```bash
synapse --verify
```

3. List available bundles:
```bash
synapse --list-bundles
```

4. Review output:
   - **Satisfaction rate** shows how often routed skills are helpful
   - **Top skills** shows your most reliable skills
   - **Needs improvement** shows skills that may need review
   - **Verify** confirms all skill files exist on disk
