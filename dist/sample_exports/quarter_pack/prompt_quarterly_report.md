# Prompt: draft the quarterly performance report

Use this with Microsoft 365 Copilot or any other AI tool your organisation allows. Attach, or point it at, the files in this folder, then paste everything below the line.

You can also use the pack without AI: open the Excel file and work through the sheets in the order of the report sections below.

---

You are helping write the quarterly performance report for 2026-27 Q2. Use **only** the attached files. Read `README_for_AI.md` and `data_dictionary.csv` first so you understand every column.

Write the report in plain UK English, for senior leaders who have two minutes. Use these sections:

1. **Summary** (five bullet points at most): overall position, the biggest improvement, the biggest concern, and what needs a decision.
2. **Measures**, grouped by `category`:
   - a table with measure (`source_ref` and `measure_name`), latest value with its unit, target, RAG and the direction of travel from the previous period;
   - for every red or amber measure, one or two sentences from its `narrative` explaining why and what is being done.
3. **Delivery**: the main work completed this quarter (`tasks` with `status` complete), grouped by what it `contributes_to_name`, and notable successes from `weekly_updates`.
4. **Problems and risks**: open problems with high impact or high urgency, who owns them and their target date, then problems resolved this quarter.
5. **Data notes**: measures with `no_data`, values marked `provisional` or `estimated` in `data_quality`, and measures with no target.

Rules:
- Never invent or estimate numbers. If something isn't in the files, say "not available".
- Quote measure codes (for example PM-0007) so every statement can be checked.
- Percentages are stored as 0 to 100: show 58 as 58%.
- Use `polarity` when you describe change: for lower-is-better measures, a fall is an improvement.
- Use `aggregation_method` if you combine monthly or weekly values into a quarter figure, and say that you did.
- Don't name individuals when you describe problems or workload; use team names.
- Finish with a short list of questions the report owner should check before publishing.
