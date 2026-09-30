import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import json
import torch
import torch.nn as nn
from PIL import Image

def generate_fixtures():
    # Create directories
    os.makedirs('data/fixtures/images', exist_ok=True)
    os.makedirs('data/fixtures/labels', exist_ok=True)
    os.makedirs('models/fixtures', exist_ok=True)

    # 1. Dummy Image (100x100 Red Square)
    img = Image.new('RGB', (100, 100), color = 'red')
    img_path = 'data/fixtures/images/dummy_001.jpg'
    img.save(img_path)

    # 2. Dummy YOLO Label (Class 0, x_center=0.5, y_center=0.5, width=0.2, height=0.2)
    with open('data/fixtures/labels/dummy_001.txt', 'w') as f:
        f.write("0 0.5 0.5 0.2 0.2\n")

    # 3. Dummy PyTorch Model
    class DummyModel(nn.Module):
        def __init__(self):
            super().__init__()
            self.linear = nn.Linear(10, 2)
        def forward(self, x):
            return self.linear(x)

    model = DummyModel()
    torch.save(model.state_dict(), 'models/fixtures/dummy_model.pt')
    
    print("Fixtures generated successfully.")

if __name__ == "__main__":
    generate_fixtures()
