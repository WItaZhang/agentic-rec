import os
import subprocess
import sys


def test_string_history_floating_point_reduction_is_stable_across_process_hash_seeds():
    script = """
from scipy import sparse
from src.model import ItemKNNModel
model = ItemKNNModel(('a', 'b', 'c'), sparse.csr_matrix([[1e16, 0, 0], [1, 0, 0], [1, 0, 0]]), (3, 2, 1))
print(model.score_items({'a', 'b', 'c', 'unknown'}).tolist())
"""
    outputs = [subprocess.check_output([sys.executable, '-c', script],
               env={**os.environ, 'PYTHONHASHSEED': str(seed)}, text=True).strip() for seed in (1, 2, 3)]
    assert outputs == ['[1e+16, 0.0, 0.0]'] * 3
