# Fairshot Virtual FDE: Demo Briefing Packet

**TLDR:**
- **What it is:** A fully automated AI system that integrates complex HR software (ATS) with Fairshot in seconds, replacing weeks of manual engineering work.
- **Why it matters:** It eliminates the biggest bottleneck to onboarding new enterprise customers, acting as an instant, zero-cost "Forward Deployed Engineer" (FDE).
- **The "Wow" factor:** The system dynamically detects when a vendor changes their data format (schema drift) and auto-repairs the integration live, without human intervention.

---

## 1. Context: What Does Fairshot Do?

Before explaining the demo, here is a quick refresher on our core business and why this demo is so important:

**Our Core Product:** Fairshot is an AI-powered talent assessment platform. We sell B2B software to large enterprises that allows them to conduct automated, AI-driven interviews and assessments for their job candidates (such as case studies, technical tests, and behavioral interviews).

**The Big Problem:** To actually sell our product to a large enterprise, we *have* to integrate with the HR software they already use (Applicant Tracking Systems like Workday, Oracle, or SmartRecruiters). If we don't, their recruiters would have to manually copy and paste candidate data between their system and Fairshot, which is a dealbreaker. 

Because enterprise HR systems are notoriously messy, customized, and unique to each company, building this integration usually takes a team of engineers weeks or months for *every single new customer*. 

**How This Demo Fits In:** This demo is not about our core AI interview product. It is about the **Virtual FDE (Forward Deployed Engineer)** — our solution to the massive integration bottleneck. It proves to investors and CTOs that we can automatically build the bridge between a customer's messy HR system and Fairshot in under 60 seconds, allowing us to onboard new enterprise customers instantly and scale without hiring an army of integration engineers.

## 2. What Is This Demo?

When a large company buys Fairshot, they need to connect their existing HR system (like Workday or Oracle) to our platform so candidate data can flow back and forth. Normally, this process requires a team of engineers to spend weeks studying the customer's specific setup, writing custom code to translate their data into our format, and testing it. We call the engineers who do this work "Forward Deployed Engineers" (FDEs).

This demo showcases our "Virtual FDE" — an autonomous AI system that does this exact job in under 60 seconds. You simply point the system at the customer's HR database, and the AI automatically figures out how their data is organized, decides how it should map to Fairshot, writes the translation code, and tests it. It turns a months-long professional services engagement into a push-button deployment.

## 2. The Problem It Solves

Integrating Applicant Tracking Systems (ATS) or Human Resources Information Systems (HRIS) is the biggest headache in B2B HR software. Here is why it is so painful:

- **Every company uses a different system:** Some use Workday, others use SmartRecruiters, Oracle, Greenhouse, or Lever. Each system operates entirely differently.
- **Data is stored inconsistently:** Even within the same system, data is messy. One company might store a candidate's first name as `firstName`, another as `Name_Data.First_Name`, and an older system might call it `CAND_FIRST_NAME_50`.
- **Customization means custom engineering:** Because every customer's setup is uniquely messy, every new customer requires a custom-built integration. This takes weeks of expensive engineering time.
- **Integrations break constantly (Schema Drift):** When an ATS vendor updates their software or a customer adds a new custom field, the data structure changes. The integration silently breaks, and engineers have to scramble to fix it. 

## 3. What the Demo Shows (Step by Step)

When you click "Start Integration" on the dashboard, the system kicks off an automated pipeline. Here is exactly what is happening:

**Step 1 — Schema Exploration:** The AI reads the customer's ATS data structure (called a "schema" — think of it as a blueprint of how their data is organized). It crawls through the blueprint, discovering every field, identifying what type of data it holds, checking if it's required, and mapping out how deeply nested the information is.

**Step 2 — Semantic Mapping:** The AI figures out which field in the customer's system corresponds to which field in Fairshot. For example, it realizes that the customer's obscure `cand_email_primary_v3_Final` field should map to Fairshot's `email` field. It detects this automatically, figuring out how to convert date formats, translate dropdown options, and clean up messy data.

**Step 3 — Code Generation:** The AI doesn't just draw lines between fields; it actually writes the translation code (Python middleware) needed to reliably convert the customer's records into Fairshot records. A second, completely independent AI (Google Gemini) acts as a reviewer, checking the generated code for correctness and edge cases.

**Step 4 — Live Data Flow Test:** The generated code is immediately put to the test. A messy, realistic candidate record from the customer's system is fed into the pipeline, and a clean, perfectly formatted Fairshot record comes out the other side. This proves the integration works in practice, not just in theory.

**Step 5 — Schema Drift (The Bonus/Wow Moment):** To show how resilient the system is, you can trigger a "schema drift" (simulating a vendor updating their API by renaming fields or changing date formats). The system instantly detects the breaking changes, figures out what went wrong, and automatically rewrites the integration code to repair itself — all in seconds, with zero engineers involved.

## 4. What's on the Screen (UI Guide)

Here is a guide to the dashboard so you know exactly what to point at and talk about during the recording:

- **Sidebar:** This is your control center. It's where you select which ATS system you want to integrate (e.g., Workday Enterprise, SmartRecruiters) and where you click the "Start Integration" button.
- **Hero Metrics:** The four big numbers at the top of the screen. Point out the timer counting the seconds, the total number of fields discovered, the percentage of fields successfully mapped (Coverage), and the AI's Confidence Score.
- **Progress Narrative:** The loading bar and status messages that update in real-time as each stage of the pipeline runs, explaining what the AI is currently thinking and doing.
- **Stage Summaries:** The green checkmarks and dropdown boxes that appear as each stage completes. You can click these to show the audience the actual fields discovered, the mappings made, and the real Python code the AI generated.
- **The Result Section:** The split-screen table at the bottom that appears at the end. It shows the messy input data on the left and the clean, transformed Fairshot output on the right.
- **Schema Explorer Tab:** A separate tab at the top of the screen. Click this before or after the main run to browse the raw, nested ATS blueprints interactively. It proves to the audience that we are dealing with real, complex enterprise data structures.

## 5. What's Real vs What's Simulated

For transparency with technical audiences, here is exactly what is real and what is mock data:

- **REAL:** The AI reasoning. GPT-4o and Gemini 2.5 Pro are genuinely analyzing the data blueprints, making semantic connections, and writing fresh translation code every single time you click start. The field mapping, code generation, and cross-validation are not pre-recorded, hardcoded, or cached.
- **SIMULATED:** The ATS schemas (the blueprints) are local mock data files, not live internet connections to Workday or Oracle servers.
- **WHY IT MATTERS:** The field names, nesting, and structural messiness in our mock files are based entirely on real-world API documentation for Workday, SmartRecruiters, and Oracle. The hardest part of this problem is the AI reasoning to untangle that mess — and that part is 100% real. The fact that the data comes from a local file instead of a live web request is irrelevant to the core technical achievement.

## 6. The Tech Stack (Plain English + Technical Detail)

If the CTO asks how it is built, use these explanations:

- **Dashboard:** The user interface you interact with.
  - *Technical Detail:* Built with Streamlit, a rapid Python web framework that allows for real-time streaming updates.
- **AI Models:** The "brains" doing the reading, mapping, and writing.
  - *Technical Detail:* Uses OpenAI's GPT-4o for schema exploration, semantic mapping, and code generation. It uses Google's Gemini 2.5 Pro as an independent cross-validator to double-check the work.
- **Orchestrator:** The manager that keeps the AI on track and moves data from step to step.
  - *Technical Detail:* A deterministic (predictable, rule-based) Python pipeline using the OpenAI Agents SDK. It is not an unpredictable "AI Agent" running wild; it is strict code that coordinates specific LLM worker tasks.
- **Code Generation:** How the AI writes the translation software.
  - *Technical Detail:* The AI does not output raw, risky text. It outputs a structured specification (JSON), which is then fed into Jinja2 templates (a safe text-replacement engine) to render deterministic Python code. This eliminates random syntax errors.
- **Schema Drift Detection:** How the system knows when an external API changes.
  - *Technical Detail:* It uses hash-based fingerprinting. Every field in the blueprint is assigned a unique cryptographic hash. If a vendor changes a field, the hash changes, triggering an instant detection and repair loop.

## 7. Key Talking Points for the Video

Here are 5 specific things to say or highlight while you record:

1. **Highlight the speed:** "Notice the timer counting up — this entire integration, which normally takes a team of engineers weeks, just completed in under 60 seconds."
2. **Highlight the complexity:** (While on the Schema Explorer tab) "These are real Workday API field structures. Look at how deeply nested and messy this is. We aren't testing on simple data."
3. **Highlight the accuracy:** "Watch the confidence score — 0.92 means the AI is highly confident in its semantic mappings, even when translating cryptic abbreviations."
4. **Highlight the adaptability:** "Now I'll switch from Workday to SmartRecruiters. It's a completely different naming convention, and the system adapts and rewrites the integration instantly."
5. **Highlight the self-healing (The Wow Moment):** "I'm going to click 'Trigger Schema Drift'. The imaginary vendor just changed 3 fields and broke the API. Watch the system catch the error and auto-repair the code in seconds. No engineer was paged."

## 8. Anticipated CTO Questions (and Answers)

A technical CTO (especially one from Palantir) will likely ask these questions:

- **"Is the AI actually doing the mapping or is this pre-computed?"**
  - *Answer:* The AI is doing it live. We do not use cached or hardcoded mappings. Every time you run the pipeline, the LLM reads the schema, performs semantic matching, and generates fresh code.
- **"How do you handle schema changes in production?"**
  - *Answer:* We use hash-based fingerprinting on the incoming data schema. If the hash changes, our pipeline intercepts the failure, re-explores the drifted schema, updates the specific field mappings, and regenerates the middleware automatically.
- **"What's your accuracy/confidence threshold?"**
  - *Answer:* The Semantic Mapper assigns a confidence score (0.0 to 1.0) to every field. We require high confidence (>0.9) for full automation. Lower confidence mappings are flagged for a quick human-in-the-loop review, which still saves 99% of the time.
- **"How does this scale to 50+ ATS vendors?"**
  - *Answer:* Because it's a semantic engine, we don't build 50 different connectors. We maintain one master Fairshot API spec, and the Virtual FDE dynamically maps any new ATS to our standard. 
- **"What's the latency in production vs this demo?"**
  - *Answer:* This demo runs the entire setup phase, which takes ~60 seconds. In production, this setup only happens *once* during customer onboarding. The generated Python middleware is what runs on live data streams, and that executes in milliseconds.
- **"Why not just use a universal API standard like HR Open Standards?"**
  - *Answer:* Because enterprise vendors don't strictly adhere to them. Even when they claim to, clients add custom fields (like `Custom_Req_ID_v3_Final`). A rigid standard breaks; a semantic mapper adapts.

## 9. How to Run the Demo

Step-by-step instructions for launching and running the demo on your machine:

1. Open your Terminal application.
2. Navigate to the project folder by typing: `cd ~/fairshot`
3. Activate the virtual environment: `source venv/bin/activate`
4. Start the dashboard with this command: 
   `PYTHONPATH=/Users/macbookair/fairshot streamlit run app/dashboard.py --server.headless true`
5. Open your web browser and go to: `http://localhost:8501`
6. *Note: Ensure your `.env` file is properly configured with valid `OPENAI_API_KEY` and `GEMINI_API_KEY` values before running.*
