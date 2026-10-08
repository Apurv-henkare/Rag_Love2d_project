# Step 1: Creating Our Test Exam Paper (`rag_golden.jsonl`)

**Files Used:**
- **Script we ran:** [`run_step1.py`](file:///d:/Python_AIP_second/run_step1.py)
- **Test file created:** [`data/eval/rag_golden.jsonl`](file:///d:/Python_AIP_second/data/eval/rag_golden.jsonl) (15 questions)
- **Saved results:** [`reports/step1_benchmark.json`](file:///d:/Python_AIP_second/reports/step1_benchmark.json)

---

## 1. What Is Step 1 About? (Simple Explanation)

Imagine we want to prove that our **Phase 2 Love2D RAG Chatbot** is better than Phase 1. To prove that, we first need an **"Exam Paper"** with **15 test questions** and their **official Answer Key**.

Instead of making up the Answer Key by hand, our script ([`run_step1.py`](file:///d:/Python_AIP_second/run_step1.py)) opened our actual vector database ([`faiss_index/`](file:///d:/Python_AIP_second/faiss_index)) and checked **which exact PDF files and page numbers** actually hold the answers.

> **🗣️ What to tell the Professor:**
> *"In Step 1, we built a 15-question Golden Benchmark (`rag_golden.jsonl`). Instead of guessing which PDFs have the answers, we queried our actual `faiss_index/` database so every question is linked to the real PDF filename and page number in our index."*

---

## 2. How We Split the 15 Questions Into 3 Simple Groups

We divided the 15 questions into 3 groups so we test everything our chatbot is supposed to do:

### **Group A: 8 Theory & API Questions (`Q01` to `Q08`)**
- **What they ask:** Normal questions about Love2D functions (like *"What does `love.update(dt)` do?"* or *"How do you draw a circle with `love.graphics.circle`?"*).
- **How we grade them:** Did the search engine find the right PDF page, and did the chatbot explain the right function name?

### **Group B: 2 Lua Coding Questions (`Q09` and `Q10`)**
- **What they ask:** Write actual Love2D Lua code (e.g., *"Move a rectangle when the right arrow key is pressed"* or *"Load and play a sound file"*).
- **How we grade them (Important!):** We **do NOT** check if the code matches word-for-word, because two programmers can write working code using different variable names (like `x` vs `player_x`). Instead, we check **`expected_apis`** — did the code use the right Love2D functions (`love.update`, `love.draw`, `love.keyboard.isDown`, `love.graphics.rectangle`)?

> **🗣️ What to tell the Professor about Coding Questions:**
> *"For coding questions, exact string matching is impossible because variable names and formatting always change. So we grade coding answers by checking **API Function Recall**—making sure the code calls the exact required Love2D functions from the documentation."*

### **Group C: 5 Out-of-Scope Trap Questions (`Q11` to `Q15`)**
- **What they ask:** Trick questions that are **NOT** in the Love2D manual—like Unity C#, Unreal Engine C++, React web apps, baking a pizza, and a **fake made-up Love2D function** (`love.graphics.draw3DRaytracedMesh`).
- **How we grade them:** The chatbot **must refuse** to answer and say *"I cannot answer this based on the provided Love2D documentation."* It must not guess or make things up.

---

## 3. All 15 Questions in Our Exam Paper (`rag_golden.jsonl`)

| ID | Type | Question | What We Check (`expected_apis`) | Real PDF & Page in `faiss_index/` |
| :--- | :--- | :--- | :--- | :--- |
| **Q01** | Theory | What does `love.update(dt)` do and what is `dt`? | `love.update`, `dt` | `06-modules.pdf` (Page 847) |
| **Q02** | Theory | When is `love.load()` called and what is it used for? | `love.load` | `06-modules.pdf` (Page 612) |
| **Q03** | Theory | How do you draw a circle using `love.graphics.circle`? | `love.graphics.circle`, `fill`, `line` | `06-modules.pdf` (Page 524) |
| **Q04** | Theory | What parameters does `love.graphics.rectangle` take? | `love.graphics.rectangle`, `width`, `height` | `06-modules.pdf` (Page 444) |
| **Q05** | Theory | Difference between `"static"` and `"stream"` in audio? | `static`, `stream` | `07-tutorials.pdf` (Page 11) |
| **Q06** | Theory | How to check if a key is held down with `love.keyboard.isDown`? | `love.keyboard.isDown` | `07-tutorials.pdf` (Page 96) |
| **Q07** | Theory | How to create a physics world with `love.physics.newWorld`? | `love.physics.newWorld` | `04-other-pages.pdf` (Page 250) |
| **Q08** | Theory | Which function changes the game window title? | `love.window.setTitle` | `01-guides.pdf` (Page 19) |
| **Q09** | **Coding** | Write Lua code to move a rectangle right with the arrow key. | `love.update`, `love.draw`, `love.keyboard.isDown`, `love.graphics.rectangle` | `07-tutorials.pdf` (Page 4) |
| **Q10** | **Coding** | Write Lua code to load and play a sound file in `love.load`. | `love.load`, `love.audio.newSource`, `play` | `04-other-pages.pdf` (Page 181) |
| **Q11** | **Trap** | How do I create a 3D Rigidbody in **Unity C#**? | **Must Refuse** | *Not in Love2D Docs* |
| **Q12** | **Trap** | How do I set up an **Unreal Engine 5** Blueprint in C++? | **Must Refuse** | *Not in Love2D Docs* |
| **Q13** | **Trap** | How do I use `useState` in a **React** web app? | **Must Refuse** | *Not in Love2D Docs* |
| **Q14** | **Trap** | What is the recipe for baking a **margherita pizza**? | **Must Refuse** | *Not in Love2D Docs* |
| **Q15** | **Trap** | How do I call the fake function `love.graphics.draw3DRaytracedMesh()`? | **Must Refuse** | *Fake API — Not in Docs* |

---

## 4. What Inside Our `faiss_index/` Looks Like

When we ran [`run_step1.py`](file:///d:/Python_AIP_second/run_step1.py), it also checked all the PDFs stored inside [`faiss_index/`](file:///d:/Python_AIP_second/faiss_index):

- **Total Useful Chunks (`status = 'current'`):** `7,797` chunks
- **Chunk Size:** `600` characters max (average is `474` characters per chunk)
- **Junk Cover Pages Removed (`00-cover-contents.pdf`):** `0` chunks in the index! We marked `00-cover-contents.pdf` as `status = 'archived'` so Table-of-Contents pages never clutter our search results.

| PDF File Name | Status Tag | How Many Chunks in `faiss_index/` |
| :--- | :---: | :--- |
| `00-cover-contents.pdf` | `archived` | **0 chunks** *(Filtered out so Table-of-Contents noise is ignored)* |
| `01-guides.pdf` | `current` | `217` chunks |
| `02-types-1of2.pdf` | `current` | `1,785` chunks |
| `03-types-2of2.pdf` | `current` | `1,953` chunks |
| `04-other-pages.pdf` | `current` | `1,029` chunks |
| `05-categories.pdf` | `current` | `200` chunks |
| `06-modules.pdf` | `current` | `2,079` chunks |
| `07-tutorials.pdf` | `current` | `369` chunks |
| `08-appendices.pdf` | `current` | `164` chunks |
| `vv2.pdf` | `current` | `1` chunk *(Contains a fake API key used in Step 4 to test our security blocker)* |
