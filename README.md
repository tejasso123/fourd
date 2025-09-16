# Project Name: 4ay

## Overview
The 4ay Application is designed to handle various knowledge base operations, user authentication, and integration with external services like Google Drive. This project follows a modular and scalable architecture for efficient performance and maintainability.

## Features
- **User Authentication**: API key-based authentication with security mechanisms.
- **Document Upload & Processing**: Supports PDF, Text, Docx, Images, CSV, and Excel files.
- **Knowledge Base Management**: Stores and retrieves structured knowledge using PhiData and PgVector.
- **Real-time Metadata & Filters**: Efficient document querying with dynamic filtering.
- **Google Drive Integration**: Securely fetch and process files from Google Drive.
- **Dynamic API Routing**: Factory pattern to handle multiple request types within a single API.
- **High Performance & Scalability**: Asynchronous processing with FastAPI.

## Installation

### Prerequisites
- Python 3.12+
- PostgreSQL Database
- Redis for caching
- Pip for package management

### Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/techlead-am/fouray-flask.git
   cd fouray-flask
   ```

2. **Create a virtual environment & install dependencies**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Mac/Linux
   venv\Scripts\activate     # On Windows

   pipenv install
   ```

3. **Set up environment variables**:
   Create a `.env` file in the root directory and add:
   ```env
   OPENAI_API_KEY=your_openai_api_key
   DB_STR=postgresql+asyncpg://user:password@localhost:5432/your_database
   REDIS_URL=redis://localhost:6379/0
   SERVICE_ACCOUNT_JSON=your_google_service_account_json
   GOOGLE_DRIVE_API_KEY=your_google_drive_api_key
   take more from devs
   ```

4. **Initialize the database**:
   ```bash
   alembic upgrade head
   ```

5. **Start the application**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access API Documentation**:
   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Technologies Used
- **FastAPI**: High-performance web framework.
- **PostgreSQL + asyncpg**: Database integration.
- **PgVector**: Vector search capabilities.
- **PhiData Framework**: Knowledge base and AI-driven storage.
- **OpenAI GPT-4**: Content generation and AI processing.
- **Google Drive API**: Secure document fetching.
- **Redis**: Caching for optimized performance.
- **Alembic**: Database migration tool.

## Deployment Instructions
### **Heroku Deployment**
1. **Install Heroku CLI**:
   ```bash
   brew install heroku  # Mac
   choco install heroku # Windows
   ```
2. **Create a Procfile**:
   ```Procfile
   web: uvicorn main:app --host=0.0.0.0 --port=${PORT:-8000}
   worker: celery -A app.celery_app.mk_celery worker --loglevel=info --pool=solo
   ```
3. **Push to Heroku**:
   ```bash
   heroku login
   heroku create fouray-flask
   heroku config:set $(cat .env | xargs)
   git push heroku main
   heroku open
   ```

## License
This project is licensed under the 4ay License.

