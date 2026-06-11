# Your Endless Stories

Your Endless Stories (YES!) is a child-safe, age-aware Streamlit storybook generator powered by OCI Generative AI. It creates short personalized stories, reading hints, comprehension quizzes, transparent session scores, and a parent progress dashboard.

## Features

- Child profiles with age, interests, reading goal, and optional baseline score
- Personalized storybook generation with title, story text, vocabulary, tricky words, and quiz questions
- Reading help with phonics and decoding hints
- Quiz flow with literal, sequence, vocabulary, and inference questions
- Transparent 100-point score model inferred from quiz answers and completion
- Local SQLite persistence for profiles, stories, sessions, and progress
- Parent dashboard with score trend, recent sessions, strengths, weak areas, and recommendations
- Seed data and demo fallback for hackathon judging without live OCI credentials

## Project Structure

```text
app.py
pages/
  1_Child_Profile.py
  2_Generate_Story.py
  3_Reading_Session.py
  4_Parent_Dashboard.py
services/
  oci_genai.py
  prompts.py
  scoring.py
  storage.py
  ui.py
models/
  schemas.py
data/
  seed_data.json
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app creates `data/yes.db` automatically and loads the seed profile the first time the database is empty.

## OCI Generative AI Configuration

The app uses one wrapper function, `call_oci_genai`, for story generation, quiz generation, hint generation, and parent summaries.

Set these environment variables for live OCI generation:

```bash
export OCI_GENAI_MODEL_ID="your-model-id"
export OCI_COMPARTMENT_ID="your-compartment-ocid"
export OCI_REGION="us-chicago-1"
```

By default, the wrapper uses the OCI SDK config file at `~/.oci/config` with profile `DEFAULT`.

Optional variables:

```bash
export OCI_CONFIG_FILE="$HOME/.oci/config"
export OCI_CONFIG_PROFILE="DEFAULT"
export OCI_GENAI_ENDPOINT="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
export OCI_AUTH="api_key"
```

Supported `OCI_AUTH` values:

- `api_key`
- `resource_principal`
- `instance_principal`

To force local demo content:

```bash
export YES_DEMO_MODE=true
```

Demo mode does not call any AI provider. It uses deterministic local story, quiz, hint, and summary fallbacks.

## Scoring Model

Each reading session is scored out of 100 points:

- Comprehension: 40 points from quiz correctness
- Phonics / decoding: 20 points from vocabulary and phonics question performance
- Fluency: 15 points from literal and sequence question performance
- Independence: 15 points from answer completion, accuracy, and reduced "not sure" responses
- Consistency: 10 points from comparison with recent sessions or baseline

The saved score includes strengths, weak areas, and one recommendation for next practice.

## Demo Flow

1. Open the app with `streamlit run app.py`.
2. Select the seeded child profile, Mia, or create a new profile.
3. Choose an existing storybook or generate a new one.
4. Read the story, open the quiz, and answer the questions.
5. Review the Proficiency Dashboard for score trend, strengths, weak areas, and next practice.

## Local Data

- SQLite database: `data/yes.db`
- Seed source: `data/seed_data.json`
- Override database path with `YES_DB_PATH=/path/to/yes.db`

No cloud storage or non-OCI external service is used.
