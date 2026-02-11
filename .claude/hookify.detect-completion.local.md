---
name: detect-task-completion
enabled: true
event: prompt
action: warn
pattern: (✅.*complete|✅.*implemented|all\s+\d+/\d+\s+tests\s+passing|completed\s+implementation|finished\s+(feature|task|implementation))
---

🔔 **Task completion detected!**

I noticed you completed a task. Would you like to update the documentation?

Run: `/update-docs` to analyze changes and propose documentation updates.
