---
description: Update Synapse Skills to the latest version
---

# Update Synapse

1. Update the package:
```bash
pip install --upgrade synapse-skills
```

2. Re-download skills (updates the index and skill files):
```bash
synapse setup --force
```

3. Verify the update:
```bash
synapse --version
synapse --verify
```

4. Done! Your skills library is now up to date.
