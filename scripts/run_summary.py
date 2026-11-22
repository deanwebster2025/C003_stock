import json
from pathlib import Path
p=json.loads((Path(__file__).resolve().parents[1]/'data/events.json').read_text())
r=p['refresh']
print(f"# C003_stock refresh\n\nStatus: **{r['status']}**\n\n{r['successCount']} / {r['sourceCount']} sources checked successfully.\n")
for s in p['sources']:
    if s['status']!='ok':print(f"- {s['name']}: {s.get('error','Needs review')}")
print('\nUnavailable sources retain their last verified event data. Check the Sources & updates view for details.')
