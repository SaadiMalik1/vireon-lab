import os
import glob
import re

dir_path = "/home/ronin/Documents/n2/to be followed."
files = glob.glob(os.path.join(dir_path, "*.md"))

with open("/home/ronin/Documents/n2/scratch_summary.txt", "w") as out:
    for f in sorted(files):
        out.write(f"\n{'='*80}\n")
        out.write(f"FILE: {os.path.basename(f)}\n")
        out.write(f"{'='*80}\n")
        
        with open(f, "r", encoding="utf-8") as md:
            content = md.read()
            # Try to extract Recommendations, Action Items, or Refactoring
            sections = re.split(r'^#+\s+', content, flags=re.MULTILINE)
            for sec in sections:
                if any(keyword in sec.lower() for keyword in ["recommendation", "action item", "refactoring", "remediation", "next step", "todo"]):
                    out.write(sec.strip() + "\n\n")
