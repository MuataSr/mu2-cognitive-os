# Mu2 Cognitive OS - Teacher Guide

**Version:** 1.0.0
**Last Updated:** 2025
**Target Audience:** Classroom Teachers, Learning Specialists

---

## Table of Contents

1. [Welcome to Mu2](#welcome-to-mu2)
2. [The Red Dot System](#the-red-dot-system)
3. [The Green Dot System](#the-green-dot-system)
4. [Reading the Citation Tooltip](#reading-the-citation-tooltip)
5. [Daily Workflow](#daily-workflow)
6. [Morning Circle](#morning-circle)
7. [Focus Mode vs. Standard Mode](#focus-mode-vs-standard-mode)
8. [Troubleshooting](#troubleshooting)
9. [FERPA & Student Privacy](#ferpa--student-privacy)

---

## Welcome to Mu2

Mu2 Cognitive OS is an adaptive learning platform that helps you:

- **Track student mastery** in real-time (Green/Yellow/Red dots)
- **Identify struggling students** who need intervention
- **Provide grounded answers** with textbook citations (no AI hallucinations)
- **Support emotional well-being** through Morning Circle check-ins

### Key Promise

**All student data stays on the classroom computer.** No cloud, no analytics, no data sharing. FERPA-compliant by design.

---

## The Red Dot System

### What is a Red Dot?

A **Red Dot** means a student is **STRUGGLING** and needs your help.

### When does a student get a Red Dot?

A student is marked "Struggling" when:
- Mastery is **below 60%** AND
- The student has **practiced 3+ times**

### Example Scenarios

| Student | Skill | Mastery | Attempts | Status |
|---------|-------|---------|----------|--------|
| Darius | Quadratic Equations | 45% | 5 | 🔴 Red Dot |
| Maria | Photosynthesis | 55% | 4 | 🔴 Red Dot |
| Alex | Fractions | 30% | 2 | ⚪ No Dot (not enough attempts) |

### What should I do?

1. **Click the student's name** to see detailed mastery data
2. **Review the specific skill** they're struggling with
3. **Provide 1-on-1 support** or pair with a peer mentor
4. **Check in emotionally** - is there something else going on?

### Quick Intervention Protocol

When you see a Red Dot:
1. Ask: "How are you feeling about this topic?"
2. Ask: "What part is confusing?"
3. Use the **Citation Tooltip** to pull the exact textbook section
4. Re-teach using the textbook explanation

---

## The Green Dot System

### What is a Green Dot?

A **Green Dot** means a student has **MASTERED** a skill (mastery > 90%).

### Why celebrate Green Dots?

- **Builds confidence** - Students see their progress
- **Frees up time** - You can focus on Red/Yellow dots
- **Enables peer mentoring** - Green dot students can help others

### What should I do?

1. **Acknowledge the achievement** publicly or privately
2. **Offer the next challenge** - Keep them engaged
3. **Consider peer tutoring** - Pair them with a Yellow/Red dot student

---

## Reading the Citation Tooltip

### What is the Citation Tooltip?

Every answer from Mu2 includes a **citation** showing exactly which textbook page the information came from. This prevents "AI hallucinations" (made-up answers).

### How to Read It

When you hover over or click a citation, you'll see:

```
📖 Source: OpenStax College Physics, Chapter 5
📄 Section: Fluid Mechanics
🔗 Page: 127 (digital edition)
```

### Why This Matters

| Without Citations | With Citations (Mu2) |
|-------------------|---------------------|
| "Photosynthesis converts sunlight to energy" | "Photosynthesis converts sunlight to energy (OpenStax Biology, Ch 4, p. 89)" |
| Could be wrong | Verifiable source |
| Trust issues | Trust through transparency |

### Classroom Example

**Student asks:** "How do water pumps work?"

**Mu2 responds with citation:**
> Water pumps are devices that move fluids by mechanical action...
>
> 📖 Source: OpenStax College Physics, Chapter 5: Fluid Mechanics

**You can:**
1. Open the physical textbook to Chapter 5
2. Show the student the exact page
3. Build trust by verifying the source

---

## Daily Workflow

### Morning (Before Class)

1. **Open the Teacher Dashboard**
   - Go to: http://localhost:3000/teacher
   - Login with your teacher credentials

2. **Review Overnight Activity**
   - Check which students practiced (if any)
   - Note any new Red Dots that appeared
   - Identify Green Dots to celebrate

3. **Run Morning Circle**
   - See [Morning Circle](#morning-circle) below

### During Class

1. **Monitor Real-Time Mastery**
   - Keep the dashboard open on a second screen
   - Refresh to see live updates as students practice

2. **Intervene on Red Dots**
   - Prioritize students with Red Dots
   - Use the Citation Tooltip to pull textbook sections

3. **Celebrate Green Dots**
   - Acknowledge achievements publicly
   - Consider peer tutoring arrangements

### After Class

1. **Review the Day's Data**
   - Check overall class progress
   - Note students who need extra support tomorrow

2. **Prepare Tomorrow's Lessons**
   - Use mastery data to inform lesson planning
   - Identify skills that need reteaching

---

## Morning Circle

### What is Morning Circle?

Morning Circle is a daily emotional check-in that helps you understand how students are feeling **before** learning begins.

### How It Works

1. **Students respond to a prompt:**
   - "How are you feeling today?"
   - "What's on your mind?"

2. **System analyzes sentiment:**
   - Positive (happy, excited) → Standard Mode
   - Negative (tired, stressed, sad) → **Focus Mode**

3. **You see a dashboard:**
   - Overall class mood
   - Individual students who may need support

### Why It Matters

Research shows that **emotional state directly impacts learning**. Morning Circle helps you:

- Catch students who are struggling emotionally
- Adjust your teaching approach for the day
- Build trust and connection with students

### Example: Darius's Story

**Morning Circle Check-in:**
- Darius: "I'm tired... stayed up late studying"
- Sentiment Score: 0.3 (negative)
- **System Action:** Suggests Focus Mode, alerts teacher

**Teacher Response:**
- "Thanks for sharing, Darius. Let's take it easy today."
- Activates Focus Mode for Darius (simplified interface)
- Checks in privately later in the day

---

## Focus Mode vs. Standard Mode

### Standard Mode

**Best for:** Most students, most days

**Features:**
- Full-featured interface
- Multiple tools and options
- Rich media content

### Focus Mode

**Best for:** Students who are overwhelmed, tired, or struggling

**Features:**
- Simplified, high-contrast interface
- Fewer distractions
- One question at a time
- Larger text, clearer navigation

### When to Suggest Focus Mode

- Student reports feeling tired or overwhelmed
- Student has multiple Red Dots (cognitive overload)
- After a stressful event (test, conflict, etc.)

### How to Activate

**Automatically:** The system will suggest Focus Mode based on Morning Circle sentiment.

**Manually:** Go to Student Settings → Toggle "Focus Mode"

---

## Troubleshooting

### Problem: Student can't log in

**Solution:**
1. Check that the student's ID is correct
2. Verify the student is in your class roster
3. Contact IT admin

### Problem: Citations don't appear

**Solution:**
1. Check internet connection (for textbook access)
2. Verify the textbook is loaded in the system
3. Try refreshing the page

### Problem: Dashboard shows old data

**Solution:**
1. Refresh the page (F5 or Ctrl+R)
2. Check that the backend service is running:
   - Open http://localhost:8000/health
   - Should see: `"status": "healthy"`

### Problem: Red Dot won't go away

**Solution:**
1. This is normal - mastery takes time
2. Review the specific skill with the student
3. Considerreteaching the concept
4. Red Dots disappear when mastery reaches 60%

---

## FERPA & Student Privacy

### What Data is Collected?

- **Learning progress:** Mastery levels, practice attempts
- **Emotional check-ins:** Morning Circle responses (sentiment only)
- **Usage data:** Time spent, features used

### What Data is NOT Collected?

- ❌ No analytics or tracking
- ❌ No data sent to the cloud
- ❌ No sharing with third parties
- ❌ No personal information beyond what's necessary

### How is Data Protected?

- **Local storage:** All data stays on the classroom computer
- **No internet required:** Works offline after initial setup
- **Teacher access only:** Students cannot see each other's data
- **Masked IDs:** Student IDs are partially hidden for privacy

### Your Responsibilities

1. **Keep your password secure**
2. **Log out when done** for the day
3. **Don't share student data** outside the classroom
4. **Report any privacy concerns** to your IT admin

---

## Quick Reference Card

```
╔═══════════════════════════════════════════════════════════╗
║  Mu2 Teacher Quick Reference                               ║
╠═══════════════════════════════════════════════════════════╣
║  🔴 Red Dot    = Struggling (mastery < 60%, 3+ attempts)  ║
║  🟡 Yellow Dot = Learning (60-90% mastery)                ║
║  🟢 Green Dot  = Mastered (> 90% mastery)                ║
║                                                           ║
║  📖 Citation    = Verifiable textbook source              ║
║  🎯 Focus Mode  = Simplified interface for overwhelmed    ║
║                                                           ║
║  Dashboard:    http://localhost:3000/teacher              ║
║  Health Check: http://localhost:8000/health               ║
╚═══════════════════════════════════════════════════════════╝
```

---

## Need Help?

**Contact your IT admin** for:
- Technical issues
- Account access
- Feature requests

**Contact your instructional coach** for:
- Pedagogical questions
- Classroom implementation strategies
- Student intervention protocols

---

**Thank you for using Mu2 Cognitive OS!**

Remember: The technology is here to support **you** and **your students**. You are the expert in your classroom - Mu2 is just a tool to help you do what you do best.
