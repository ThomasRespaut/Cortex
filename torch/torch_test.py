import torch
import torch.nn as nn
from torch.nn import functional as F
import numpy as np
import time
device = 'cuda' if torch.cuda.is_available() else 'cpu'
print(device)


start_time = time.time()
# matrix operations here
zeros = torch.zeros(1, 1)
end_time = time.time()

elapsed_time = end_time - start_time
print(f"{elapsed_time:.8f}")