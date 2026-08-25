# /// script
# dependencies = ["pywin32"]
# ///
"""Render the task-3 Sanofi pptx to PDF via PowerPoint COM. Writes only inside the task dir."""
import os, sys, win32com.client

D = r"C:\Users\neuma_p1qrsic\Repo\agentic-ops1-leadgen-task-3\output\leadgen-task-3\collateral-pack"
stems = sys.argv[1:] or ["brisken-treasurycentral-sanofi"]
ppt = win32com.client.Dispatch("PowerPoint.Application")
for stem in stems:
    pres = ppt.Presentations.Open(os.path.join(D, stem + ".pptx"), WithWindow=False)
    pres.SaveAs(os.path.join(D, stem + ".pdf"), 32)
    n = pres.Slides.Count
    pres.Close()
    print(f"{stem}.pdf ({n} slides)")
ppt.Quit()
print("done")
