# Planorama

[![Paper](https://img.shields.io/badge/Paper-EMNLP%202025-blue)](https://nbalepur.github.io/assets/pdf/Planorama.pdf)
[![Dataset](https://img.shields.io/badge/Dataset-HuggingFace-orange)](https://huggingface.co/datasets/nbalepur/Planorama-user-data)

> **A Good Plan is Hard to Find: Aligning Models with Preferences is Misaligned with What Helps Users**  
> EMNLP 2025

This repository contains the code for **Planorama**, the interface developed for our EMNLP 2025 paper.  

📄 [Read the paper](https://nbalepur.github.io/assets/pdf/Planorama.pdf)  
📊 [Explore the dataset](https://huggingface.co/datasets/nbalepur/Planorama-user-data)  

---

## 🚀 Local Development

### 1. PostgreSQL Setup
Install PostgreSQL. A quick option is via Conda:

```bash
conda install anaconda::postgresql
```

Initialize a database cluster (⚠️ WSL users: prefer a subdirectory under `$HOME`):

```bash
mkdir datadir
pg_ctl -D datadir initdb
pg_ctl -D datadir -l logfile start
```

Create the user and database:

```bash
createuser -s postgres
createdb -U postgres -h localhost -p 5432 kuiperbowl
```

Then, configure `web/.env.local` from `.env` with your credentials.

---

### 2. Application Setup

Create and activate a virtual environment:

```bash
conda create -n helpfulness
conda activate helpfulness
conda install pip
```

Install dependencies & set up:

```bash
cd web
pip install -r requirements.txt
python manage.py migrate
```

Start Redis for channel layers (via Docker):

```bash
docker run -p 6379:6379 -d redis:5
```

Load fixtures:

```bash
python manage.py loaddata fixtures/question_fixtures.json
python manage.py loaddata fixtures/document_fixtures.json
```

Run the server:

```bash
python manage.py runserver --insecure
```

---

## 📚 Entering Question Data

Our math and trivia questions can be loaded directly from the repository:
```bash
cd web
python scripts/pb_load.py
python manage.py loaddata fixtures/sanity_tutorial_questions.json
python manage.py loaddata fixtures/question_fixtures.json
```

---

## 🐳 Using Docker

### Quick Start

1. Configure `.env` with the correct credentials.  
2. Build and run:

```bash
docker-compose up --build
```

---

## 📖 Citation

If you use this code or dataset, please cite our EMNLP 2025 paper:

```
@inproceedings{balepur2025planorama,
  title={A Good Plan is Hard to Find: Aligning Models with Preferences is Misaligned with What Helps Users},
  author={Balepur, N. and others},
  booktitle={Proceedings of the 2025 Conference on Empirical Methods in Natural Language Processing (EMNLP)},
  year={2025}
}
```
