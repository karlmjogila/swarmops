# Content Uploader UI - Testing Guide

## 🧪 Quick Visual Test

### Start the Application

```bash
# Terminal 1: Backend
cd /opt/swarmops/projects/hl-bot-v2/backend
poetry run uvicorn hl_bot.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Frontend
cd /opt/swarmops/projects/hl-bot-v2/frontend
npm run dev
```

Then open: http://localhost:5173/ingest

---

## ✅ Visual Checklist

### Layout
- [ ] Two-column grid on desktop (YouTube | PDF)
- [ ] Single column on mobile
- [ ] Dark theme with consistent colors
- [ ] Icons visible (📺 📄)

### YouTube Form
- [ ] URL input field with placeholder
- [ ] Blue "Submit YouTube URL" button
- [ ] Button shows spinner when loading
- [ ] Button disabled when empty or loading

### PDF Form
- [ ] File picker with custom styling
- [ ] Shows filename when file selected
- [ ] Only accepts PDF files
- [ ] Blue "Upload PDF" button

### Job List
- [ ] "Processing Jobs" header with refresh button
- [ ] Empty state shows 📭 icon and message
- [ ] Jobs sorted newest first

### Job Cards
- [ ] Status icon (⏳ ⚙️ ✅ ❌)
- [ ] Colored badge (yellow/blue/green/red)
- [ ] Progress bar with gradient (for active jobs)
- [ ] Relative timestamps ("2m ago", "Just now")
- [ ] Error messages (red background)
- [ ] Success messages (green background)
- [ ] Pulse animation on processing jobs

---

## 🎬 Test Scenarios

### Scenario 1: Submit YouTube URL

1. Navigate to `/ingest`
2. Paste URL: `https://youtube.com/watch?v=dQw4w9WgXcQ`
3. Click "Submit YouTube URL"
4. **Expected:**
   - Button shows spinner
   - New job appears in list with "PENDING" badge
   - Progress bar at 0%
   - After 1-2 seconds: changes to "PROCESSING"
   - Progress bar animates to 100%
   - Badge changes to "COMPLETED" (green)

### Scenario 2: Upload PDF

1. Click "Choose PDF file..."
2. Select any PDF file
3. **Expected:**
   - File name shows below button
   - "Upload PDF" button becomes enabled
4. Click "Upload PDF"
5. **Expected:**
   - Similar flow to YouTube
   - New job appears and processes

### Scenario 3: Error Handling

1. Try uploading a `.txt` file (not PDF)
2. **Expected:**
   - Error banner appears
   - "Please select a PDF file"
   - File input resets

### Scenario 4: Multiple Jobs

1. Submit 2-3 YouTube URLs
2. Upload 1-2 PDFs
3. **Expected:**
   - All jobs visible in list
   - Active jobs poll every 2 seconds
   - Completed jobs show strategy count
   - Jobs sorted by time (newest first)

---

## 📸 Screenshots to Capture

1. **Empty state** - No jobs yet
2. **YouTube form** - URL entered
3. **PDF form** - File selected
4. **Processing job** - Blue badge, progress bar
5. **Completed job** - Green badge, success message
6. **Failed job** - Red badge, error message
7. **Mobile view** - Single column layout
8. **Multiple jobs** - List with mixed statuses

---

## 🐛 Common Issues & Fixes

### Issue: "Failed to fetch"
**Cause:** Backend not running  
**Fix:** Start backend on port 8000

### Issue: Jobs not updating
**Cause:** Polling not working  
**Fix:** Check browser console for errors

### Issue: PDF upload fails
**Cause:** File size or type  
**Fix:** Use PDF under 50MB

### Issue: CORS error
**Cause:** Frontend/backend on different origins  
**Fix:** Check CORS settings in `main.py`

---

## 🎨 UI Components Used

```typescript
// From ContentUploader.svelte
<input class="input" />           // Dark input with focus ring
<button class="btn btn-primary">  // Blue button with hover
<div class="card">                // Dark card with border
<span class="badge badge-*">      // Colored status badges
<div class="progress-bar">        // Animated progress
<div class="job-card">            // Job item container
```

---

## 📊 API Testing (curl)

```bash
# Submit YouTube URL
curl -X POST http://localhost:8000/api/ingest/youtube \
  -H "Content-Type: application/json" \
  -d '{"url": "https://youtube.com/watch?v=dQw4w9WgXcQ"}'

# Upload PDF
curl -X POST http://localhost:8000/api/ingest/pdf \
  -F "file=@test.pdf"

# List all jobs
curl http://localhost:8000/api/ingest/jobs

# Get specific job
curl http://localhost:8000/api/ingest/jobs/{job_id}
```

---

## ✨ Expected Behavior

### Timeline for a successful job:

```
0s    - Submit → Job created (PENDING, 0%)
0-1s  - Background task starts (PROCESSING, 10%)
1-3s  - Processing content (PROCESSING, 60%)
3-5s  - Finalizing (PROCESSING, 90%)
5s    - Complete (COMPLETED, 100%, shows strategy count)
```

### Auto-polling:
- Starts when component mounts
- Polls every 2 seconds
- Only active when jobs are processing
- Stops when all jobs are done/failed

---

## 🎯 Success Criteria

✅ All forms functional  
✅ Jobs tracked correctly  
✅ Progress updates visible  
✅ Error handling works  
✅ UI responsive on mobile  
✅ Dark theme consistent  
✅ Animations smooth  
✅ Timestamps human-readable  

---

*Ready to test? Start both servers and visit /ingest!*
