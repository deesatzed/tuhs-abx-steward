# 🚀 RUN THE FIXED SYSTEM - Quick Start

## **What's Been Fixed**

✅ **Tiered sequential search** (reputable sites first, then broader)  
✅ **Confidence-gated** (triggers on TUHS confidence, not complexity)  
✅ **Reputable site tier** (IDSA/CDC/WHO specifically)  
✅ **Agno backend** (uses multi-agent system)  
✅ **Connected to existing index.html**

---

## **Step 1: Install Flask**

```bash
cd /Volumes/WS4TB/claude_abx_bu930/claude_abx/phase2
source venv_agno/bin/activate
pip install flask flask-cors
```

---

## **Step 2: Start Agno Backend**

```bash
python agno_bridge.py
```

**You should see:**
```
🚀 Starting Agno Backend Bridge...
📡 Connect your Express frontend to: http://localhost:5000
 * Running on http://0.0.0.0:5000
```

---

## **Step 3: Test It Works**

### **Test 1: High Confidence (No Search)**
```bash
curl -X POST http://localhost:5000/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age": 55, "gender": "M", "location": "Ward", "infection_type": "pneumonia", "gfr": 80, "allergies": "none"}'
```

**Expected:** No external search, confidence ≥ 0.8

### **Test 2: Moderate (Reputable Sites)**
```bash
curl -X POST http://localhost:5000/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age": 78, "gender": "F", "location": "ICU", "infection_type": "uti", "gfr": 35, "allergies": "none", "history_resistance": "ESBL"}'
```

**Expected:** Searches IDSA/CDC/WHO only

### **Test 3: Low (Both Tiers)**
```bash
curl -X POST http://localhost:5000/api/recommendation \
  -H "Content-Type: application/json" \
  -d '{"age": 88, "gender": "M", "location": "ICU", "infection_type": "bacteremia", "gfr": 22, "allergies": "penicillin (anaphylaxis)", "history_mrsa": true}'
```

**Expected:** Searches reputable sites, THEN PubMed

---

## **Step 4: Connect Frontend (Choose One)**

### **Option A: Update index.html**
Change API endpoint in `public/index.html`:
```javascript
// Find the fetch call and change to:
fetch('http://localhost:5000/api/recommendation', {
  method: 'POST',
  // ...
})
```

### **Option B: Express Proxy**
Update `server.js` to proxy to Agno:
```javascript
app.post('/api/recommendation', (req, res) => {
  // Forward to Agno bridge
  fetch('http://localhost:5000/api/recommendation', {
    method: 'POST',
    body: JSON.stringify(req.body)
  })
  // ...
});
```

---

## **🎯 Verify Workflow**

Watch the terminal output to see:

**High Confidence:**
```
✅ Category: pneumonia
✅ TUHS Confidence: 85%
✅ Decision: No external search needed
```

**Moderate Confidence:**
```
✅ Category: uti
✅ TUHS Confidence: 70%
🔍 Searching reputable sites (confidence: 70%)
✅ Confidence improved to 75% - stopping search
```

**Low Confidence:**
```
✅ Category: bacteremia
✅ TUHS Confidence: 55%
🔍 Searching reputable sites (confidence: 55%)
🔍 Confidence still low (60%) - searching broader sources
✅ Search complete - Final confidence: 68%
```

---

## **📊 System Architecture**

```
User → index.html → Flask Bridge → Agno Agents
                       ↓
                    1. TUHS Category Agent (FIRST)
                    2. Calculate Confidence
                    3. IF < 0.8 → Reputable Sites
                    4. IF < 0.6 → PubMed
                    5. Return Result
```

---

## **✅ What To Check**

- [ ] Flask bridge starts without errors
- [ ] curl tests return JSON responses
- [ ] Confidence scores are visible
- [ ] Search tier matches confidence level
- [ ] Sequential search works (reputable first)
- [ ] Stops when confidence improves

---

**Read `OPTION_A_FIXED.md` for complete details!**
