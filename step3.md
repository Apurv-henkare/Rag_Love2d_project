# Step 3: Checking the AI's Answers, Citations & Refusals (`run_step3.py`)

**Files Used:**
- **Script we ran:** [`run_step3.py`](file:///d:/Python_AIP_second/run_step3.py)
- **Questions tested:** All 15 questions (`Q01` to `Q15`) from [`data/eval/rag_golden.jsonl`](file:///d:/Python_AIP_second/data/eval/rag_golden.jsonl)
- **Saved results:** [`reports/step3_grounding.json`](file:///d:/Python_AIP_second/reports/step3_grounding.json)

---

## 1. What Is Step 3 About? (In Plain English)

In Step 2, we checked if our **Search Engine** could find the right PDF pages.
Now in Step 3, we check the **AI's Final Answers** on all **15 questions** from our test paper (`rag_golden.jsonl`).

We want to prove **3 simple things** to the professor:
1. **No Made-Up Facts (Citations `[1]`, `[2]`):** Whenever the AI states a fact about Love2D, it must put a number in brackets like `[1]` or `[2]` showing which PDF paragraph it used.
2. **Working Lua Code (`expected_apis`):** When asked to write Lua code (`Q09` and `Q10`), the AI uses the real Love2D functions from the manual.
3. **Honest "I Don't Know" on Trick Questions (Refusals):** When asked about things that are **not** in the Love2D manual (like Unity C#, Unreal Engine, React, baking bread, or a fake function), the AI refuses to guess and says:
   > *"I don't have enough information in the provided sources to answer that."*

---

## 2. The 4 Metrics Explained in Everyday Language

Here is how to explain the 4 scores in our table to your professor in plain English:

### 1. **Citation Validity (`100%`) — *"Did the AI show real proof?"***
- **What it means:** When we give the AI 5 paragraphs from the PDF (numbered `[1]` to `[5]`), did the AI actually cite those numbers in its answer? And did it only use real numbers (for example, citing `[1]` or `[3]` is valid, but citing `[99]` is fake because there is no paragraph 99)?
- **Simple Formula:**
  $$\text{Citation Validity} = \frac{\text{Answers with real, valid } [1]\dots[k] \text{ citations}}{\text{Total Love2D Questions Answered}}$$
- **Our Score:** **`100%` (`10 out of 10` Love2D questions had valid citations!)**

---

### 2. **API Recall (`100%`) — *"Did the answer mention the right Love2D functions?"***
- **What it means:** Every question in our test paper has a checklist of required Love2D function names (`expected_apis`).
  - For example, on Coding Question `Q09` (*"move a rectangle with arrow keys"*), the checklist has **4 required functions**: `love.update`, `love.draw`, `love.keyboard.isDown`, and `love.graphics.rectangle`.
  - If the AI's code includes all 4 functions, its score is `4/4 = 100%`.
- **Why we use this for code:** Two programmers can write different variable names (`speed` vs `vel`), so checking exact code text doesn't work. Checking the required Love2D function names is fair and reliable.
- **Simple Formula:**
  $$\text{API Recall} = \frac{\text{How many required Love2D functions appeared in the answer}}{\text{Total required functions on our checklist}}$$
- **Our Score:** **`100%` (`8/8` on Theory and `2/2` on Coding!)**

---

### 3. **Refusal Recall (`100%`) — *"Did the AI catch all 5 trick questions?"***
- **What it means:** We gave the AI **5 trick questions (`Q11` to `Q15`)** that are outside the Love2D manual (Unity, Unreal, React, baking bread, and a fake 3D raytracing function). **Refusal Recall** asks: *"Out of those 5 trick questions, how many did the AI properly refuse?"*
- **Simple Formula:**
  $$\text{Refusal Recall} = \frac{\text{Trick questions the AI properly refused}}{\text{Total trick questions (5)}}$$
- **Our Score:** **`100%` (`5 out of 5` trick questions refused — 0 hallucinations!)**

---

### 4. **Refusal Precision (`100%`) — *"When the AI refused, was it actually a trick question?"***
- **What it means:** Imagine a lazy chatbot that says *"I don't know"* to **every** question—even real Love2D questions! That lazy bot would catch all the trick questions, but it would be useless for real questions.
  - **Refusal Precision** checks that the AI **only** refuses trick questions, and **never** refuses a real Love2D question (`0` false alarms).
- **Simple Formula:**
  $$\text{Refusal Precision} = \frac{\text{Trick questions refused (5)}}{\text{Total times the AI refused across all 15 questions (5)}}$$
- **Our Score:** **`100%` (`5 / 5` — Zero false refusals on real Love2D questions!)**

> **🗣️ How to explain Refusal Recall vs. Refusal Precision to the Professor in 2 sentences:**
> - **Refusal Recall (`100%`)** means: *"We caught 5 out of 5 trick questions without making anything up."*
> - **Refusal Precision (`100%`)** means: *"We had zero false alarms—the bot never said 'I don't know' on a real Love2D question."*

---

## 3. How Our Python Code Forces `100%` Valid Citations (`validate_answer`)

Why did we get `100%` Citation Validity? Because we don't just trust the AI—we check its work in Python!

In [`chain.py`](file:///d:/Python_AIP_second/chain.py#L401-L435), our function `validate_answer()` runs a strict check on every AI response:
1. It checks that the answer contains bracket numbers like `[1]` or `[2]`.
2. It checks that every bracket number is between `1` and the number of chunks we actually gave the AI.
3. **Auto-Repair Retry:** If the AI ever forgets a `[1]` citation or makes a mistake, Python automatically sends it back to the AI once saying: *"You forgot a valid citation—fix it now."*

---

## 4. Summary Table by Question Group (Table 1)

| Question Group | How Many Questions | Citation Validity | API Check / Refusal Score | Final Pass Score |
| :--- | :---: | :---: | :---: | :---: |
| **Group A: Love2D Theory (`Q01`–`Q08`)** | `8` | **`100.0%`** | **`100.0%` APIs Mentioned** | **`8 / 8` (`100%`)** |
| **Group B: Lua Coding (`Q09`–`Q10`)** | `2` | **`100.0%`** | **`100.0%` Code APIs Used** | **`2 / 2` (`100%`)** |
| **Group C: Trick / Out-of-Scope (`Q11`–`Q15`)** | `5` | *Refused cleanly* | **`100.0%` Refusal Recall** | **`5 / 5` (`100%`)** |
| **TOTAL ACROSS ALL 15 QUESTIONS** | **`15`** | **`100.0%` Valid** | **`100.0%` Refusal Precision** *(0 False Alarms)* | **`15 / 15` (`100%`)** |

---

## 5. Results for Every Single Question (`Q01` to `Q15`)

| ID | Type | Citations Used by AI | Checklist Score | Time Taken | Pass/Fail |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **Q01** (`love.update(dt)`) | Theory | `[1, 2, 3, 4]` | `2/2` APIs (`100%`) | `2.8 sec` | **PASS** |
| **Q02** (`love.load()`) | Theory | `[3, 4]` | `1/1` APIs (`100%`) | `2.0 sec` | **PASS** |
| **Q03** (`love.graphics.circle`) | Theory | `[4]` | `3/3` APIs (`100%`) | `3.0 sec` | **PASS** |
| **Q04** (`love.graphics.rectangle`) | Theory | `[1, 2]` | `3/3` APIs (`100%`) | `3.3 sec` | **PASS** |
| **Q05** (`static` vs `stream`) | Theory | `[1, 4]` | `2/2` APIs (`100%`) | `2.3 sec` | **PASS** |
| **Q06** (`love.keyboard.isDown`) | Theory | `[1, 2, 3, 4]` | `1/1` APIs (`100%`) | `3.5 sec` | **PASS** |
| **Q07** (`love.physics.newWorld`) | Theory | `[2, 3, 4]` | `1/1` APIs (`100%`) | `2.7 sec` | **PASS** |
| **Q08** (`love.window.setTitle`) | Theory | `[2, 3]` | `1/1` APIs (`100%`) | `2.2 sec` | **PASS** |
| **Q09** (Move rectangle Lua code) | **Coding** | `[3, 11, 15, 18]` | **`4/4` Code APIs (`100%`)** | `5.1 sec` | **PASS** |
| **Q10** (Load & play sound code) | **Coding** | `[1, 4, 6, 7, 8, 10]` | **`3/3` Code APIs (`100%`)** | `6.0 sec` | **PASS** |
| **Q11** (Unity C# `Rigidbody`) | **Trap** | `[]` *(Refused)* | **Refused Properly** | `3.0 sec` | **PASS** |
| **Q12** (Unreal Engine 5 C++) | **Trap** | `[]` *(Refused)* | **Refused Properly** | `2.0 sec` | **PASS** |
| **Q13** (React `useState` web app) | **Trap** | `[]` *(Refused)* | **Refused Properly** | `2.3 sec` | **PASS** |
| **Q14** (Baking sourdough bread) | **Trap** | `[]` *(Refused)* | **Refused Properly** | `1.4 sec` | **PASS** |
| **Q15** (Fake `draw3DRaytracedMesh`) | **Trap** | `[]` *(Refused)* | **Refused Properly** | `2.1 sec` | **PASS** |

---

## 6. Why Theory Questions Take ~2.5 Seconds and Coding Questions Take ~5.5 Seconds

> **🗣️ Great point to mention to the Professor:**
> *"In Phase 1, our bot made **2 AI calls** for every single question, which wasted time. In Phase 2 ([`chain.py`](file:///d:/Python_AIP_second/chain.py#L142-L167)), we added a smart rule in Python:*
> - *If the user asks a **simple theory question (`Q01`–`Q08`)**, Python skips the extra search-planning call and goes straight to FAISS search—answering in just **~2.5 seconds** with **1 AI call**.*
> - *If the user asks to **write code (`Q09`–`Q10`)**, Python uses the Search Planner to search for all the different pieces needed (game loop + keyboard input + drawing/audio), so the AI has 100% of the functions it needs to write working code."*

---

## 7. Three Real Examples From Our Run

### **1. Theory Answer (`Q01` — Cites `[1][2][3][4]`):**
> **Question:** *"What does `love.update(dt)` do and why is `dt` important?"*
> **AI Answer:** *"The `love.update(dt)` function is a callback used to update the state of the game every frame [3]. It is called continuously and is the primary location for performing game logic and math [4]. The parameter `dt` (delta-time) represents the amount of time in seconds that has passed since the function was last called [2][3][4]. By multiplying a speed value by `dt`, you ensure that objects move at a consistent speed regardless of how fast the processor runs [1][2][4]."*

### **2. Coding Answer (`Q09` — Uses all `4/4` required `love.*` functions + cites `[3, 11, 15, 18]`):**
> **Question:** *"Write Lua code to move a rectangle on screen using arrow keys and delta time `dt`..."*
> **Checklist Checked:** `love.update` ✅, `love.draw` ✅, `love.keyboard.isDown` ✅, `love.graphics.rectangle` ✅ (`4/4 = 100%`)

### **3. Out-of-Scope Trap (`Q11` & `Q15` — Refuses cleanly with `0%` hallucination):**
> **Question:** *"How do I write a C# MonoBehaviour script with Rigidbody in Unity?"*
> **AI Answer:** *"I don't have enough information in the provided sources to answer that."*
