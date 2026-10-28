"""Scaffold a project from the template.  usage: python new_project.py DIR"""
import sys, os, shutil
src = os.path.join(os.path.dirname(__file__), "..", "..", "templates", "project")
dst = os.path.abspath(sys.argv[1])
if os.path.exists(os.path.join(dst, "edit.py")): raise SystemExit(f"{dst} already has edit.py — refusing to overwrite")
os.makedirs(dst, exist_ok=True)
for f in os.listdir(src): shutil.copy(os.path.join(src, f), os.path.join(dst, f))
for d in ("raw/img", "build", "out"): os.makedirs(os.path.join(dst, d), exist_ok=True)
print("created", dst, "->", sorted(os.listdir(dst)))
