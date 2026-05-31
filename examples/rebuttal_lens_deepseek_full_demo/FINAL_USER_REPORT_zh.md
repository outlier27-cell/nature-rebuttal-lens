# Nature RebuttalLens 最终作者回应辅助报告

本报告是 assistant 输出，不是可直接提交的最终 rebuttal。所有实验、证据、引用和承诺都必须由作者确认。

## 1. 核心判断

系统识别出 3 个 reviewer concern。其中 1 个 claim 暂时不可追溯或证据不足。建议先补证据和缩窄承诺，再组织 rebuttal 草稿。

## 2. Reviewer Concern Cards

### comment_001 - experimental_design

- 表层要求：The authors should provide a more transparent account of the split construction, add robustness checks under at least one temporally held-out split, and clarify whether the reported gains remain when near-duplicate review-response pairs are removed.
- 深层风险：The dataset appears to be drawn from multiple Nature-family journals over several years, yet the manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits. It is also unclear whether papers from the same journal issue, topic cluster, or review round can appear across different splits.
- 证据状态：partially_supported / section_004
- 证据缺口：No explanation of how temporal leakage was avoided or whether papers from the same journal issue, topic cluster, or review round can appear across different splits.
- 建议动作：Explanation of how temporal leakage was avoided in dataset splits
- 作者确认必需：True
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid claiming that the concern is fully resolved before evidence is available.

### comment_002 - generalization_scope

- 表层要求：Without this, the central claim that the method generalizes across peer-review contexts is overstated.
- 深层风险：The central claim that the method generalizes across peer-review contexts is overstated.
- 证据状态：missing / none
- 证据缺口：No evidence provided to support the claim that the method generalizes across peer-review contexts, especially regarding temporal and topical robustness.
- 建议动作：Robustness checks under temporally held-out splits
- 作者确认必需：True
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid claiming that the concern is fully resolved before evidence is available.

### comment_003 - clarity_presentation

- 表层要求：The manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits.
- 深层风险：The manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits.
- 证据状态：supported / section_007
- 证据缺口：The manuscript acknowledges the lack of temporal split validation and potential topical clustering, but does not provide detailed methods to address these issues.
- 建议动作：Revised claims about generalization scope
- 作者确认必需：True
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid overstating implications beyond the supplied manuscript evidence.

## 5. 推荐回应结构

- Thank the reviewer and restate the concern as an evidence/validity issue.
- Address comment_001 by explaining: Explanation of how temporal leakage was avoided in dataset splits.
- Address comment_002 by explaining: Robustness checks under temporally held-out splits.
- Address comment_003 by explaining: Revised claims about generalization scope.
- Do not overclaim until this missing element is resolved: Specific details on how temporal leakage will be avoided in the new analyses.
- Do not overclaim until this missing element is resolved: Quantitative evidence to support the narrowing of generalization claims.
- Close by distinguishing completed revisions from analyses that require author confirmation.

## 6. 作者必须确认的问题

- Should we prioritize temporal split validation over other planned analyses?
- Are there known topical clusters that require explicit stratification?
- What proportion of records support full interaction chain analysis?
- Explanation of how temporal leakage was avoided in dataset splits
- Robustness checks under temporally held-out splits
- Revised claims about generalization scope

## 7. 不安全或不可追溯的 claim

- The method generalizes across peer-review contexts（source: none）

## 8. Responsible Use

- assistant_only
- author_must_verify_all_claims
- not_final_rebuttal_text
- no_acceptance_prediction
- no_confidential_upload_recommendation
