# Virtual FDE — Demo Script

## Pre-Demo Checklist
- [ ] `.env` populated with `OPENAI_API_KEY` and `GOOGLE_API_KEY`
- [ ] `pip install -r requirements.txt` completed
- [ ] `streamlit run app/dashboard.py` running on localhost
- [ ] Browser in dark mode / full screen
- [ ] Practice run completed at least once

## Demo Flow (~90 seconds total)

### Opening (15 seconds)
> "What you're about to see is an autonomous system that replaces
> weeks of manual enterprise integration work with a single click.
> No configuration. No data plumbing. No FDE required."

### Step 1: Start Integration (5 seconds)
1. Select **"Workday Enterprise"** from the dropdown
2. Click **"Start Integration"**
3. Point out: "This is a real Workday-like schema — 50+ fields,
   deeply nested, custom naming conventions, mixed date formats."

### Step 2: Schema Exploration (~10 seconds)
- Watch the Schema Explorer panel populate in real-time
- Call out: "The system is autonomously crawling the schema,
  discovering every field, detecting naming patterns like
  `_v3_Final` suffixes, and flagging anomalies."
- Point to the field count and nesting depth metrics

### Step 3: Semantic Mapping (~15 seconds)
- Watch mappings appear with confidence colors
- Call out: "Each field is semantically matched — the system
  understands that `cand_nm_first` means `first_name`, that
  `addr_city_nm` maps to `location.city`, and that epoch
  timestamps need conversion to ISO 8601."
- Point to the green/yellow confidence indicators
- Click "Unmapped ATS Fields" to show deprecated fields were
  correctly identified and skipped

### Step 4: Code Generation (~10 seconds)
- Watch the generated Python appear in the code panel
- Call out: "The system generates production-style middleware
  and cross-validates it with a second AI model — Gemini 2.5 Pro.
  Two sets of eyes on every transform, just like a real code review."
- Point to the "Data flow test passed" indicator

### Step 5: Live Data Flow (~10 seconds)
- Point to the Input/Output panels
- Call out: "Here's a real candidate record flowing through the
  generated middleware. Messy Workday format in, clean Fairshot
  API payload out. Zero data loss."
- Pause for effect: "Total time: under 60 seconds."

### Step 6: Schema Drift — THE WOW MOMENT (~20 seconds)
1. Say: "But what happens when Workday pushes an update?"
2. Click **"Trigger Schema Drift"**
3. Point to the drift alert: "Three breaking changes detected —
   a field renamed, a new required field added, a date format changed."
4. Watch the auto-repair flow:
   - "The system re-explores the changed schema..."
   - "Re-maps only the affected fields..."
   - "Regenerates the middleware..."
   - "Tests the data flow again..."
5. Point to the green confirmation: "Auto-repaired. Zero manual
   intervention. This is what Palantir charges $300K/year for
   a human FDE to do."

### Closing (5 seconds)
> "This is the Virtual FDE. Weeks of integration work,
> compressed to seconds. Self-healing. Anti-fragile.
> Ready to deploy at every enterprise client."

## Talking Points by Audience

### For Mattia (Technical)
- "Zero-touch integration — no manual data plumbing"
- "Dual-LLM architecture — anti-fragile, no single-model dependency"
- "Hash-based schema drift detection — O(1) per field"
- "Deterministic Jinja2 templating — no LLM-generated syntax errors"

### For Alberto (Strategy)
- "Compresses months-long onboarding to minutes"
- "Enables Fairshot to scale to any ATS without scaling headcount"
- "TAM expansion — every enterprise client is now self-service"

### For Luca (Capital)
- "Eliminates professional services cost center"
- "Compliance-aware — skips sensitive PII fields automatically"
- "Risk reduction — every transform is cross-validated"

## Troubleshooting
- **Pipeline hangs:** Check API keys in `.env`. Check network.
- **Slow response:** First run is cold. Re-run is faster.
- **Schema drift fails:** Verify `workday_drift.json` exists in `src/mock_data/`.
- **Dashboard not updating:** Refresh browser. Check terminal for errors.