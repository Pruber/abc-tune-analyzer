import os
from pathlib import Path

def create_dummy_data():
    base_dir = "abc_books" 
    
    # We know the base_dir exists, but this ensures the path is correct
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # Create books 0, 1, and 2
    for i in range(3):
        folder_name = str(i)
        folder_path = os.path.join(base_dir, folder_name)
        os.makedirs(folder_path, exist_ok=True)
        
        # Write two sample tunes into each book file
        content = f"""X:{i}01
T:The Test Reel {i}
R:Reel
M:4/4
K:D
ABCD EFGH|
%---
X:{i}02
T:The Quick Jig {i}
R:Jig
M:6/8
K:G
GBdB GBdB|
"""
        with open(os.path.join(folder_path, f"sample{i}.abc"), "w") as f:
            f.write(content)
            
    print("✅ Mock data creation SUCCESS.")

if __name__ == "__main__":
    create_dummy_data()
