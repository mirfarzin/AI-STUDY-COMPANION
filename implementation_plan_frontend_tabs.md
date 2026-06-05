# Add Frontend Feature Tabs (PYQ, Quiz, Weak Topics)

## Goal
Implement three new UI tabs in the Vite/React frontend: PYQ Solver, Quiz Generator, and Weak Topics analysis. Wire them into the existing navigation alongside the Chat tab, provide full UI components, API integration, localStorage persistence, and responsive Tailwind styling.

## User Review Required
- Confirm the naming of the new view state (`'weak'`) in `App.jsx`.
- Approve the added helper functions in `api.js` (if any adjustments needed).

## Open Questions
- Do you want the Weak Topics tab to appear always in the navigation bar, or only after a quiz is completed? (Current plan adds it permanently.)
- Should the subject dropdown include an explicit "All Subjects" entry for PYQ (already requested) – yes.

## Proposed Changes
---
### Frontend
#### [MODIFY] [App.jsx](file:///c:/Users/mirfa/OneDrive/Desktop/antigrav/study%20companions/frontend/src/App.jsx)
- Extend `view` state to include `'weak'`.
- Add a new button in the tab bar for **Weak Topics** with the `Brain` icon.
- Pass additional props `weakData` and `setWeakData` to `WeakTopicsPane`.

#### [NEW] [PYQPane.jsx](file:///c:/Users/mirfa/OneDrive/Desktop/antigrav/study%20companions/frontend/src/components/PYQPane.jsx)
- Dropdown for 14 subjects + **All Subjects**.
- Textarea for user question.
- Call `solvePYQ(question, subject)` from `api.js`.
- Show loading spinner, error handling (HTTP 400 → friendly message), answer text, and collapsible source cards.
- Use Tailwind for layout and mobile responsiveness.

#### [NEW] [QuizPane.jsx](file:///c:/Users/mirfa/OneDrive/Desktop/antigrav/study%20companions/frontend/src/components/QuizPane.jsx)
- Subject dropdown (14 subjects) and difficulty selector (Easy/Medium/Hard).
- Fetch quiz via `generateQuiz(subject, difficulty)`.
- Render one question at a time with four options.
- On answer click, highlight correct (green) and incorrect (red), show explanation.
- Track score and collect wrong questions.
- Final screen: show `Score X/5`, **Retry** button (reset state), **See Weak Topics** button.
- On **See Weak Topics**, POST to `/api/weak-topics` with collected wrong questions, store result in App state, switch view to `'weak'`.
- Persist wrong questions per subject to `localStorage` under key `quiz_history_{subject}` and merge on each quiz run.

#### [NEW] [WeakTopicsPane.jsx](file:///c:/Users/mirfa/OneDrive/Desktop/antigrav/study%20companions/frontend/src/components/WeakTopicsPane.jsx)
- Accept props: `subject`, `weakTopics` (array) and `onBack`.
- Optional manual trigger: subject dropdown + **Analyze** button that calls `analyzeWeakTopics`.
- Render each topic as a Tailwind chip; clicking expands to show advice (use `<details>`/`<summary>` or custom accordion).
- Load any persisted wrong‑question history from `localStorage` on mount (key `quiz_history_{subject}`).
- UI responsive and mobile‑first.

#### [MODIFY] [api.js](file:///c:/Users/mirfa/OneDrive/Desktop/antigrav/study%20companions/frontend/src/api.js)
- Ensure existing exports `solvePYQ`, `generateQuiz`, `analyzeWeakTopics` are correctly typed.
- No new dependencies; all calls already use the axios instance.
- Add a tiny helper to map HTTP 400 to a user‑friendly error if needed (optional).

---
### Backend (no code changes needed beyond existing endpoints)
- The backend already provides `/api/pyq`, `/api/quiz`, `/api/weak-topics` with proper 400 handling.

## Verification Plan
### Automated
- Run `npm run dev` and ensure the app builds without TypeScript/ESLint errors.
- Use the browser to navigate each new tab:
  1. **PYQ** – submit a sample question, verify answer and source cards appear.
  2. **Quiz** – complete a full 5‑question flow, verify scoring, wrong‑question collection, and that the **See Weak Topics** button fetches data.
  3. **Weak Topics** – display topics, expand advice, and confirm that manual subject selection works.
- Refresh the page and confirm that previously stored wrong‑question history persists (check `localStorage`).
- Verify that `/health` endpoint still returns 200 via a quick curl.

### Manual
- Open the Vercel preview URL and test on a mobile viewport (375 px) to confirm responsive layout.
- Open the browser console and ensure no errors appear during any interaction.
- Confirm that HTTP 400 responses from the backend show the message **"Could not generate response, try again"**.

---
**All changes will be made within the existing repository at** `c:\Users\mirfa\OneDrive\Desktop\antigrav\study companions`.
