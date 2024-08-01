# GCP_social_jam
It is a FastAPI-based application designed to automatically generate content for businesses based on their business model and past engagement data. The project leverages AI to create posts that align with a brand's objectives and share them on social media platforms, enhancing online presence and engagement.

## Goal

The primary goal of this project is to:
- Analyze past company engagement data.
- Generate content that aligns with the brand's objectives.
- Share generated posts on social media platforms.


## Getting Started

### Prerequisites

- Python 3.10
- FastAPI
- Vertex AI access and setup
- BigQuery setup with relevant access
- API keys and credentials as needed

### Installation

1. **Clone the repository:**
   ```sh
   git clone https://github.com/harshkalra-ai/GCP_social_jam.git
   cd GCP_social_jam
   ```

2. **Create a virtual environment and activate it:**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory with the necessary API keys and credentials.

5. **Run the application:**
   ```sh
   uvicorn Main:app --port 8000 --reload
   ```
