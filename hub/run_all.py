"""Run the full SMASH-BIO hub pipeline in order."""
import runpy
import sys
import time

STEPS = ["s01_harvest_articles", "s02_harvest_datasets", "s03_classify", "s04_links",
         "s05_fulltext", "s06_build_records", "s07_build_site"]

if __name__ == "__main__":
    start = sys.argv[1] if len(sys.argv) > 1 else STEPS[0]
    for s in STEPS[STEPS.index(start):]:
        t = time.time()
        print(f"=== {s}", flush=True)
        sys.argv = [s + ".py"]
        runpy.run_module(s, run_name="__main__")
        print(f"=== {s} done in {time.time() - t:.0f}s", flush=True)
