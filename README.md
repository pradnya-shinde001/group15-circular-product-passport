# AI-Powered Circular Economy Product Passport

Group 15, Capstone Project, FH Dortmund.
**Homework Assignment 4:** error handling with our own exception classes, and automated tests with pytest, on top of the web app and shared database from Assignment 3.

A digital passport for electronic products: a unique identity and QR code, a tamper-evident lifecycle history, a circularity score and AI advice.

## Team

| Team member        | Subsystem                                | Folder                                        |
| ------------------ | ---------------------------------------- | --------------------------------------------- |
| Mosaddeka Mallick  | 1. Passport, QR code and web UI          | [subsystem1_passport](subsystem1_passport/)   |
| Anishkumar Sukumar | 2. Event ledger (tamper-evident history) | [subsystem2_ledger](subsystem2_ledger/)       |
| Rajib Munshi       | 3. Circularity score engine              | [subsystem3_score](subsystem3_score/)         |
| Pradnya Shinde     | 4. AI engine (advice)                    | [subsystem4_ai_engine](subsystem4_ai_engine/) |

**Video:** TODO

## Run it

Tested with Python 3.14. Run the commands from the project folder.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://localhost:8000 for the pages and http://localhost:8000/docs for the API. On its first start, the app creates the database with demo data. To rebuild it, stop the app and run `python -m database.seed`. This also deletes products you registered yourself.

**Optional, AI advice from the LLM:** copy `.env.example` to `.env` and add your KI:connect.NRW key, created at https://chat.kiconnect.nrw under API key management. Without a key, the AI engine uses its rules. Git ignores `.env`.

## Logins

Reading passports is public. To register a product or record an event, log in at `/login`, or sign up at `/signup` as a consumer, manufacturer or recycler. The four demo accounts below use the password `demo-password`, for the local demo only.

| Email | May do |
| ----- | ------ |
| `admin@example.com` | Register products, record every event type |
| `manufacturer@example.com` | Register products; record manufactured, sold, repaired, refurbished |
| `recycler@example.com` | Record refurbished, recycled |
| `consumer@example.com` | Record sold, used, repaired |
