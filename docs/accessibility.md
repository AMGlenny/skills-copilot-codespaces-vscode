# Accessibility (WCAG 2.2 AA)

Both apps are designed to meet WCAG 2.2 AA. Some of that is checked automatically on every change, and the rest needs a person with a keyboard, a screen reader and a phone before go-live.

## Checked automatically (`tests/test_accessibility.py`)

| WCAG | What's checked |
|---|---|
| 1.4.3 Contrast (minimum) | Every text colour on every background is at least 4.5:1. The ratio is worked out from the actual colour values. The old grey header was about 2:1; the new one is over 11:1. |
| 1.4.11 Non-text contrast | Input borders and focus rings are at least 3:1 |
| 1.3.1 Info and relationships, 2.4.6 Headings | Each screen has exactly one main heading, with section headings under it |
| 4.1.2 Name, role, value | Every text box, dropdown, combo box, date picker and gallery has an accessible name, and every clickable icon has a label |
| 2.1.1 Keyboard | Every clickable icon can be reached with Tab |
| 2.4.7 Focus visible | Every button has a thick focus border |
| 2.5.8 Target size (minimum) | Buttons and icons are at least 24 by 24 pixels. Most are 40 or more. |
| 1.4.10 Reflow | Every screen adapts to narrow widths. The columns stack on phones. |
| 4.1.3 Status messages | Save results and validation messages are announced to screen readers |
| 1.4.1 Use of colour | RAG and status are always given in words ("Red: off track", "Not yet"). Colour is extra. This is checked by review, not automatically. |

## How the design helps with the newer WCAG 2.2 criteria

- **3.3.7 Redundant entry.** Nothing is asked for twice. Your team is filled in from your profile, open tasks and problems carry over each week, and a returned value opens with its previous answers.
- **3.3.8 Accessible authentication.** Sign-in is Microsoft 365 single sign-on, so there's no separate password or puzzle.
- **2.4.11 Focus not obscured.** The apps have no sticky banners or pop-ups covering the page. Notifications appear at the top and don't take focus.
- **3.2.6 Consistent help.** Help text sits under each field, in the same place on every screen.

## Manual checks before go-live

Do these once on each app, and again after any big change. Record the results in the go-live checklist.

1. **App checker.** In Power Apps Studio, open **App checker**, then **Accessibility**. Fix every item it lists.
2. **Keyboard only.** Unplug the mouse. Go through the main task on each screen: save a weekly update, add a task, submit a value, approve one.
   - Is the tab order sensible?
   - Can you always see where focus is?
   - Can you reach and use everything?
3. **Screen reader.** Use Narrator (Windows) or NVDA. Check that:
   - headings are announced
   - each field's label is read out
   - "Saved" and error messages are spoken
   - gallery rows make sense out of context (for example, "Open task: Draft the Q2 narrative")
4. **Zoom and phone.** Try the browser at 200% zoom, then the Power Apps mobile app on a phone. Nothing should need sideways scrolling, and nothing should be cut off.
5. **Colour blindness.** Use a colour-blindness simulator (built into Edge developer tools). RAG must still be clear from the words.
6. **Plain language.** Ask a colleague who hasn't seen the app to do a weekly update without help. Note where they hesitate.

## Known limits

- **Zoom:** Power Apps canvas apps don't fully support browser text resizing (1.4.4). They scale the whole app instead. Test at 200% and note anything that clips.
- **Galleries** show a fixed amount of text per row. Long narratives are cut short in the version history, and the full text is always in the narrative box.
- **Charts:** there are none in the apps. Power BI reports built on the exports need their own accessibility check.
