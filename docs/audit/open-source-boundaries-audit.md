# Open-Source Boundaries Audit

## Verification Date: 2026-05-28

### Section 9.1: Should Be Open-Sourced ✓/✗

- **README**: **PRESENT** ✓ (2.1KB)
- **Schema**: **PRESENT** ✓ (`review_interaction_unit.schema.json`)
- **Taxonomy**: **PRESENT** ✓ (9 taxonomy files)
- **Evaluation protocol**: **PRESENT** ✓ (`EVALUATION_PROTOCOL_zh.md`)
- **Agent framework**: **PRESENT** ✓ (documented in multiple files)
- **Responsible use policy**: **MISSING** ✗

#### Taxonomy Files (9 total):
1. `author_positioning_taxonomy.v1.json`
2. `concern_taxonomy.v1.json`
3. `editor_signal_taxonomy.v1.json`
4. `evidence_action_taxonomy.v1.json`
5. `institutional_signal_taxonomy.v1.json`
6. `response_strategy_taxonomy.v1.json`
7. `skill_taxonomy.v1.json`
8. `tacit_concern_taxonomy.v1.json`
9. `tone_commitment_taxonomy.v1.json`

#### Documentation Files Present:
- `DATA_CARD_zh.md` - Data card
- `AGENT_CARD_zh.md` - Agent card
- `EVALUATION_PROTOCOL_zh.md` - Evaluation protocol
- `DATA_RELEASE_BOUNDARY_zh.md` - Data release boundaries
- Multiple design and specification documents

### Section 9.2: Cautious Open-Source ✓/✗

- **Full review/response texts**: **PRESENT** ⚠️
  - Review text: ~300 chars average
  - Response text: ~759 chars average
  - **Status**: Texts are present but appear to be excerpts/snippets, not full texts
  - **Source**: Nature transparent peer review (public data)
  - **Justification**: These are from publicly available transparent peer review, so redistribution is acceptable

- **Provenance links only**: **YES** ✓
  - All 245 units have `provenance` field
  - All units have `source_url` for traceability
  - All units have `doi` for paper identification

### Section 9.3: Should NOT Be Open-Sourced ✓/✗

- **Confidential manuscripts**: **ABSENT** ✓
  - No confidential manuscript content found
  - All data from public transparent peer review

- **Acceptance prediction**: **ABSENT** ✓
  - No acceptance prediction code found
  - Multiple warnings AGAINST acceptance prediction in documentation
  - System explicitly designed to avoid acceptance prediction

- **Auto-submit functionality**: **ABSENT** ✓
  - No auto-submit code found
  - System outputs structured suggestions, not final submissions
  - Author confirmation required (documented in design)

### Responsible Use Policy Analysis

**Current Status**: README.md does NOT contain responsible use warnings

**Required Warnings (Section 11.2)**:
1. ✗ Not uploading confidential manuscripts
2. ✗ Not replacing authors/reviewers/editors
3. ✗ Author confirmation required

**However**, these warnings ARE present in:
- `DATA_RELEASE_BOUNDARY_zh.md`
- `build_naturereview_v01.py` (system prompts)
- Design documents

**Recommendation**: Add responsible use section to README.md

### Acceptance Prediction Safeguards

The codebase contains **extensive safeguards** against acceptance prediction:
- 30+ mentions of "不预测接收率" (do not predict acceptance)
- Integrity checks include `no_acceptance_prediction`
- Agent boundaries explicitly forbid acceptance prediction
- Documentation repeatedly states "not an acceptance predictor"

This demonstrates strong commitment to ethical boundaries.

### Status: **PARTIAL** ⚠️

**What's Good**:
- ✓ All required artifacts present (schema, taxonomy, evaluation protocol)
- ✓ No confidential content
- ✓ No acceptance prediction functionality
- ✓ No auto-submit functionality
- ✓ Complete provenance tracking
- ✓ Extensive ethical safeguards in code

**What Needs Fixing**:
- ✗ README.md missing responsible use warnings
- ⚠️ Full text snippets present (but from public data, so acceptable)

### Recommendations

#### Before Release:

1. **Add Responsible Use section to README.md**:
   ```markdown
   ## Responsible Use

   This system is designed to assist authors in understanding reviewer concerns and
   planning evidence-grounded responses. It is NOT:

   - An acceptance rate predictor
   - A replacement for author judgment
   - A tool for confidential manuscript analysis

   Users must:
   - Only use with publicly available peer review data
   - Confirm all suggestions before use
   - Not upload confidential manuscripts
   - Maintain author agency and decision-making
   ```

2. **Consider**: Add a `RESPONSIBLE_USE.md` file with detailed guidelines

#### Post-Release:

1. Monitor for misuse (acceptance prediction claims, auto-submission tools)
2. Add usage examples that demonstrate responsible use
3. Consider adding a license that explicitly prohibits certain uses

### Conclusion

The open-source boundaries are well-implemented with strong ethical safeguards. The only critical issue is the missing responsible use warnings in README.md, which should be added before release. The system correctly avoids all prohibited functionality and maintains complete provenance tracking.
