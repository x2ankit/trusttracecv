import os; os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import sys; sys.path.insert(0, ".")
import numpy as np
from pathlib import Path
from PIL import Image
from src.dataset.security_checks import _patch_entropy, check_trigger_patterns

trigger_dir = Path("data/fixtures/triggers/images")
for p in sorted(trigger_dir.iterdir()):
    arr = np.array(Image.open(p).convert("RGB"))
    # Slide 16x16 window and find min entropy
    min_ent = 99.0
    min_pos = None
    for y in range(0, arr.shape[0] - 16 + 1, 16):
        for x in range(0, arr.shape[1] - 16 + 1, 16):
            patch = arr[y:y+16, x:x+16]
            ent = _patch_entropy(patch)
            if ent < min_ent:
                min_ent = ent
                min_pos = (x, y)
    print(f"{p.name}: min16x16_entropy={min_ent:.4f} at {min_pos}")
