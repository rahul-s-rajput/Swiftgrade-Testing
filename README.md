# AI Mark Grading Testing App

A comprehensive application for testing and comparing AI model performance in grading student assessments.

## 🚀 Features

- **Multi-Model Testing**: Compare grading results across different AI models
- **Auto-Numbering Questions**: Backend automatically generates question numbers from array position
- **Customizable Prompts**: Full control over system, user, and schema templates via settings
- **Reasoning Support**: Per-model reasoning configuration (effort-based or token-based)
- **Flexible Parser**: Handles various response formats from different AI models
- **Detailed Analytics**: Compare AI grades against human benchmark marks

## 📁 Project Structure

```
project/
├── app/                    # Backend (FastAPI)
│   ├── routers/           # API endpoints
│   ├── schemas.py         # Pydantic models
│   └── main.py           # Application entry
├── src/                    # Frontend (React + TypeScript)
│   ├── pages/            # Main application pages
│   ├── components/       # Reusable components
│   └── utils/            # API client and utilities
├── docs/                   # All documentation
├── scripts/                # Utility scripts
│   └── sql/              # Database migrations
├── tests/                  # Test scripts
├── test_data/             # Sample data and test inputs
└── logs/                  # Application logs
```

## 🛠️ Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- Supabase account (for database and storage)
- OpenRouter API key

### Backend Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements-backend.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run backend
python -m uvicorn app.main:app --reload
```

### Frontend Setup
```bash
# Install dependencies
npm install

# Run frontend
npm run dev
```

### Database Setup
Run the SQL migrations in Supabase:
1. Go to Supabase SQL Editor
2. Run scripts from `scripts/sql/` folder in order

## 🔧 Configuration

### Environment Variables (.env)
```
OPENROUTER_API_KEY=your_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
OPENROUTER_DEBUG=1  # Enable detailed logging
```

### Custom Prompts
Navigate to Settings page to customize:
- **System template**: Instructions for the AI model
- **User template**: How to present student data
- **Schema template**: JSON response format expected

## 📝 API Documentation

### Key Endpoints

#### Session Management
- `POST /sessions` - Create new assessment session
- `GET /sessions` - List all sessions
- `DELETE /sessions/{id}` - Delete a session

#### Question Configuration
- `POST /questions/config` - Configure questions (auto-numbering supported)
- `GET /questions/{session_id}` - Get questions for a session

#### Grading
- `POST /grade/single` - Grade with selected models
- `GET /results/{session_id}` - Get grading results
- `GET /stats/{session_id}` - Get statistics and discrepancies

#### Settings
- `GET /settings/prompt` - Get prompt templates
- `PUT /settings/prompt` - Update prompt templates

### Question Format (Simplified)
```json
{
  "questions": [
    {"question_id": "Q1", "max_marks": 10},
    {"question_id": "Q2", "max_marks": 15}
  ],
  "human_marks_by_qid": {
    "Q1": 9,
    "Q2": 14
  }
}
```
Note: Question numbers are auto-generated from array position!

## 🧪 Testing

Run test scripts from the `tests/` folder:
```bash
# Test auto-numbering feature
python tests/test_auto_numbering.py

# Test reasoning configuration
python tests/test_reasoning.py

# Test backend endpoints
python tests/test_backend.py

# Test database settings
python tests/test_database_settings.py
```

## 📚 Documentation

### Key Documentation
- [Backend Documentation](docs/README-backend.md)
- [API JSON Formats](docs/API_JSON_FORMATS.md)
- [Reasoning Implementation](docs/REASONING_IMPLEMENTATION.md)
- [Frontend Input Formats](docs/FRONTEND_INPUT_JSON.md)
- [Test Inputs Guide](docs/TEST_INPUTS_README.md)

### Recent Updates
- ✅ Auto-numbering questions from array position
- ✅ Customizable schema templates in settings
- ✅ Per-model reasoning configuration
- ✅ Improved error handling and logging

## 🔍 Debugging

Enable debug mode for detailed logging:
```bash
# In .env file
OPENROUTER_DEBUG=1
```

Check logs in the `logs/` directory for session-specific debugging.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure everything works
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🙏 Acknowledgments

- OpenRouter for unified AI model access
- Supabase for backend infrastructure
- React and FastAPI communities

---

For questions or support, please open an issue in the repository.
