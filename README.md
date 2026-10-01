# CareerPilot AI

CareerPilot turns a target role and a person's existing experience into a practical next-step plan. It is a career planning aid, not a hiring prediction service. Skill gaps connect to curated learning resources, portfolio projects, resume improvements, and relevant job-search channels.

## Product Architecture

### Product principles

- **Progress over judgment:** readiness is a planning indicator with an explanation, never a verdict about a candidate.
- **Gap to action:** every important gap should lead to a reason, a manageable learning activity, an applied task, and evidence the user can later add to a resume.
- **Grounded facts:** curated JSON data owns resource URLs, portal metadata, and role skill expectations. Gemini may explain and prioritize; it may not invent links or user achievements.
- **Useful without AI:** deterministic role data and a clear service-unavailable state keep core exploration available when credentials, network, or quota are unavailable.
- **One connected journey:** career profile, gap analysis, roadmap, resume review, and the next-action summary use the same target role and profile.

### Information architecture and screens

1. **Home (`/`)** explains the product in one viewport, previews a career report, and offers `Create my career plan` and `Analyze my resume`.
2. **Career profile (`/career`)** is a six-step, save-as-you-go wizard: name; target role and experience; skills; education/projects/certifications/experience; schedule; learning preference.
3. **Career report (`/career/report`)** answers “What am I missing?” with readiness context, strong/developing/missing skills, prioritized gap-to-action recommendations, project and portal suggestions, and five next actions.
4. **Roadmap (`/roadmap`)** answers “What should I learn next?” through four collapsible weeks and 30 profile-dependent daily tasks. Each task has an objective, time estimate, activity, expected outcome, and curated resource where available.
5. **Resume analyzer (`/resume`)** accepts a PDF, DOCX, or TXT file and a target role; staged progress communicates extraction, matching, keyword review, structure review, and recommendation generation.
6. **Resume report (`/resume/report`)** presents extracted profile facts, an estimated ATS compatibility indicator with dimension-level explanations, role matching, and prioritized edits. It must never invent achievements or present the estimate as an official ATS result.
7. **Career dashboard (`/dashboard`)** is the return surface: today's mission, readiness, resume match, learning progress, profile completeness, streak, and immediate next action.
8. **Resources** is a curated-data view linked from recommendations. Interview Coach is a future module, not a Version 1 navigation promise.

### Primary user journey

Landing → six-step profile → role readiness and skill gap → 30-day roadmap → curated learning resource and gap-closing project → resume-to-role analysis → next five actions → dashboard. Resume-only users can enter at the analyzer and optionally create a profile afterward. Profile and roadmap state are recoverable within the browser; uploaded files are temporary and are not retained after analysis.

### UI component system

Shared templates/components: `Navbar`, `Footer`, `Button`, `FormField`, `StepIndicator`, `SkillChip`, `ScoreCard`, `ProgressBar`, `SkillGapGroup`, `RoadmapWeek`, `RoadmapDay`, `ResourceCard`, `ResumeUpload`, `AnalysisStage`, `RecommendationCard`, `PriorityBadge`, `ProjectCard`, `PortalCard`, `EmptyState`, `ErrorState`, `LoadingState`, and accessible `Toast`. Components receive validated view-model data; model-generated text is plain text, never HTML.

### Visual system and interaction language

- **Palette:** warm white surfaces, charcoal text, quiet gray structure, restrained burnt-orange primary actions and route/progress highlights; green, amber, and red communicate semantic status with accompanying labels. Color is not the only status cue.
- **Type:** readable sans-serif with a compact heading scale, generous body line-height, and clear label/metadata contrast.
- **Layout:** constrained reading width, generous whitespace, flat surfaces, subtle borders, medium radii, and elevation only for interactive or floating elements. Avoid generic admin grids and excessive gradients.
- **Journey motif:** one restrained path line with milestone nodes links profile → gap → learning → evidence → application. Product preview uses real interface patterns, not a robot illustration.
- **Motion:** short fade/slide entry, progress fill, accordion expansion, chip add/remove, and toast feedback; no motion is required to understand state. Honor `prefers-reduced-motion` and avoid delaying navigation.
- **Responsive:** desktop uses a compact nav and two-column report/dashboard layouts; tablet reduces columns; mobile stacks content, makes step controls and primary actions thumb-friendly, and keeps navigation compact.

### API and data flow

Browser templates and small progressive-enhancement scripts → Flask routes → validation and domain services → curated JSON knowledge base and, when configured, the Gemini service. The browser never receives the Gemini key or internal exception details.

Initial route contracts:

| Route | Method | Purpose |
| --- | --- | --- |
| `/api/health` | GET | Liveness and AI configuration status without returning secrets |
| `/career/generate` | POST | Validate profile; create readiness, categorized gaps, roadmap, resources, projects, and actions |
| `/career/report` | GET | Render the saved, validated career report |
| `/career/roadmap` | GET | Render the complete 30-day schedule in four expandable week groups |
| `/career/roadmap/complete` | POST | Record a completed day and return updated progress |
| `/resume/analyze` | POST | Validate multipart file and role; extract facts; return match, estimated ATS dimensions, and grounded recommendations |
| `/dashboard` | GET | Combine career progress and the latest resume compatibility result |
| `/resources` | GET | Browse curated learning links |

The server owns scoring and validates every structured AI response against expected fields, types, lengths, and allowed enums before rendering. Knowledge-base IDs are used to resolve links. Deterministic fallbacks preserve the essential report when Gemini is unavailable. A random opaque ID in Flask's signed cookie points to server-side SQLite profile, progress, and parsed report data that expires after 24 hours; uploaded resume bytes are processed in memory and never stored there. Validate all submitted fields again on every request.

### AI workflow and trust boundary

`career_service` assembles normalized profile facts and role expectations; `gemini_service` sends a constrained JSON-only request to Gemini; response parsing and schema validation reject malformed or oversized output; `resource_service` resolves only curated IDs; the route renders escaped text. Resume extraction precedes model use, and only extracted text needed for matching is sent. Never send the original uploaded file to the model or log its contents. Never fabricate employment, certifications, project outcomes, metrics, or external URLs.

Readiness and ATS values are transparent heuristics with visible dimensions and copy describing their limits. ATS dimensions cover keyword alignment, document structure, section organization, role relevance, skills coverage, and evidence; no score is described as an employer-system result.

### Error, loading, and recovery behavior

- Missing/invalid key, permission failure, rate limit/quota, unavailable model, invalid request, timeout, empty output, malformed JSON, and temporary provider failure map to distinct internal error codes and safe user-facing retry/fallback messages.
- Detailed provider status and traceback are logged server-side with secrets, resume text, and personal data redacted. Browser responses never contain credentials, stack traces, or raw provider payloads.
- Upload validation checks extension, size, readable content, and safe generated storage names; unsupported, corrupt, or empty files receive actionable messages. Temporary uploads are deleted after processing, including error paths.
- All major operations expose pending, success, empty, and retryable failure states. AI analysis uses labeled stages and a timeout; it does not leave a static spinner indefinitely.
- If AI output fails schema validation, make one bounded repair attempt where safe; otherwise use a deterministic fallback and record a redacted diagnostic.

### Accessibility and security

Use semantic landmarks and headings, associated labels, keyboard-operable controls, visible focus, live-region status updates, accessible progress values, descriptive errors, sufficient contrast, and reduced-motion support. Chips support add/remove without pointer-only interaction. Do not communicate gaps or scores by color alone.

Keep `GEMINI_API_KEY` in an ignored `.env`; enforce upload size/type limits; generate server-side filenames; sanitize and validate all input; escape rendered output; never render model HTML; protect state-changing forms with CSRF; rate-limit career generation to 30 and resume analysis to 8 requests per client per minute using hashed client keys; avoid retaining resumes; and do not put secrets or personal resume content in logs or analytics. For multi-instance production, move rate-limit state to shared infrastructure and run Flask behind a production WSGI server.

## Implementation Phases

1. **Foundation:** Flask app factory/config, route blueprints, templates, responsive design tokens, curated JSON data, health endpoint, README and environment setup.
2. **Career guide:** accessible six-step profile, skill chips, role matching, gap report, profile-dependent 30-day roadmap, curated resource retrieval, deterministic fallback.
3. **Resume analyzer:** bounded upload handling, PDF/DOCX/TXT extraction, role comparison, explained compatibility indicator, prioritized grounded recommendations, deletion and failure paths.
4. **Career intelligence:** project recommendations, readiness/dashboard aggregation, progress persistence, next-action synthesis, modular future interview-coach boundary.
5. **Polish:** responsive/accessibility review, reduced-motion behavior, loading/error states, security checks, performance, and a repeatable demo journey.

## Initial Project Structure

```text
careerpilot-ai/
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── config/config.py
├── routes/{career_routes,resume_routes,health_routes}.py
├── services/{gemini_service,career_service,resume_service,ats_service,resource_service,project_service}.py
├── utils/{validators,file_parser,error_handler,helpers}.py
├── prompts/{career_prompt,resume_prompt,ats_prompt,project_prompt}.txt
├── data/{career_roles,skills,resources,job_portals,certifications,project_templates}.json
├── templates/{base,index,career,career_result,resume,resume_result,dashboard}.html
├── static/css/style.css
├── static/js/{main,career,resume}.js
└── uploads/                 # temporary only; ignored by Git
```

## Local Development

Python 3.11 or newer is recommended. Create a virtual environment, install `requirements.txt`, copy `.env.example` to `.env`, and set `GEMINI_API_KEY` to enable generative explanations. The core experience remains available without the key through the deterministic planner. Start with `python app.py`; Flask serves the application locally. Do not commit `.env` or real resume files.