# Intent: runtime-based tasks

Confirmed with the maintainer on 2026-10-18.

- **Outcome:** a task can have a runtime limit, a calendar interval, or both. It's due at whichever limit comes first, and marking it done resets both.
  - The runtime limit counts hours while one linked entity is in any state other than `off`.
- **User:** the maintainer, for things that wear with use rather than time, like the air conditioner's filter.
- **Display:** a new "Remaining" sensor shows the percentage left, based on hours only. It appears on the task's device page and on the card. Hybrid tasks also keep their next due date.
- **Notifications:**
  - Hours: a warning is sent once, as soon as the remaining percentage drops below a threshold. The threshold has a global default and can be overridden per task.
  - Hours: another is sent as soon as it reaches 0%, then every morning at the notify time until the task is marked done.
  - Dates: unchanged (the day before, then every day once overdue).
- **Success:** the AC filter task warns at the threshold and again at 0%, both after real AC use. The hour count survives Home Assistant restarts.
- **Constraints:**
  - Uses the same add and change task forms and the same card as today.
  - Existing tasks keep working without changes.
  - `unavailable` and `unknown` don't count as on.
- **Out of scope:**
  - Counting only while the AC is actively cooling.
  - Linking several entities to one task.
  - Measuring wear by power or energy use.
  - Counting runtime while Home Assistant is down.
  - Percentages for the date part.
