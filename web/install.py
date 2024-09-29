import os
with open('requirements.txt', 'r') as file:
    packages = file.readlines()

for package in packages:
    os.system(f'pip install {package.strip()}')