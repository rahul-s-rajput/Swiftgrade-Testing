# Swiftgrade AI Model Testing Assistant

[![Download Latest Release](https://img.shields.io/badge/Download-Latest%20Release-blue)](https://github.com/rahul-s-rajput/Swiftgrade-Testing/releases/latest)

A specialized desktop application for testing and comparing AI model performance in grading student assessments.

## 📋 What is Swiftgrade Testing Assistant?

Swiftgrade Testing Assistant is a desktop application designed specifically for testing and comparing different AI models' performance in grading student assessments. The app allows you to:

- **Test multiple AI models** simultaneously on the same assessment data
- **Compare grading accuracy** across different models
- **Analyze performance metrics** and discrepancies
- **Generate detailed reports** on model effectiveness
- **Fine-tune prompts and configurations** for optimal results

## 🚀 Quick Start

### Step 1: Download
1. Go to [Releases](https://github.com/rahul-s-rajput/Swiftgrade-Testing/releases/latest)
2. Download the appropriate version for your operating system:
   - **Windows**: Download `swiftgrade-testing-assistant_x.x.x_x64-setup.exe`
   - **macOS**: Download `swiftgrade-testing-assistant_x.x.x_x64.dmg`
   - **Linux**: Download `swiftgrade-testing-assistant_x.x.x_amd64.AppImage`

### Step 2: Install
1. Run the downloaded installer
2. Follow the installation wizard
3. Launch the application

### Step 3: Configure
1. **Get API Keys**: Sign up at [OpenRouter.ai](https://openrouter.ai) for access to multiple AI models
2. **Configure Settings**: Enter your API keys in the Settings menu
3. **Set up Database**: Configure Supabase for storing test results

## 📖 How to Use

### Basic Testing Workflow
1. **Launch the app** and ensure your API keys are configured
2. **Create a new test session** or load existing assessment data
3. **Select AI models** to test (GPT-4, Claude, Gemini, etc.)
4. **Upload student assessment data** (responses, rubrics, human scores)
5. **Run comparative analysis** across all selected models
6. **Review results** including accuracy metrics and discrepancies
7. **Export reports** for model performance analysis

## 📋 Input Requirements & Supported Formats

### Required Input Types

The application requires two main types of inputs for effective AI model testing:

#### 1. **Assessment Questions**
Each question should include:
- **Question ID**: Unique identifier (e.g., "Q1", "Q2")
- **Maximum Marks**: Total points available (e.g., 10, 15)

#### 2. **Human Graded Student Responses**
For each question, you need:
- **Student Responses**: Actual student answers (text, can include formatting)
- **Human Benchmark Grades**: Reference grades given by human evaluators
- **Student IDs**: Unique identifiers for tracking

### Supported Input Formats

#### JSON Schema Structure
```json
{
  "questions": [
    {"question_id": "Q1", "max_marks": 10},
    {"question_id": "Q2", "max_marks": 15}
  ],
  "human_marks_by_qid": {
    "Q1": 8.5,
    "Q2": 12.0
  }
}
```

#### Student Response Format
```json
{
  "student_responses": {
    "student_001": {
      "Q1": "The main themes in the essay include...",
      "Q2": "To solve this problem: Step 1..."
    }
  }
}
```

### Configurable Response Schemas

Users can customize the AI response format through the Settings menu:

#### Alternative Schema Templates

The system supports multiple response format variations. Here are additional templates you can use:

**Simplified Question-Only Format:**
```json
Return ONLY JSON: {"answers":[{"question_id":"Q1","marks_awarded":8.5,"rubric_notes":"Good analysis"}]}
```

**Alternative Field Names:**
```json
Return ONLY JSON: {"result":[{"first_name":"John","last_name":"Doe","answers":[{"question_id":"Q1","mark":8.5,"feedback":"Well done"}]}]}
```

**Top-Level Results Format:**
```json
Return ONLY JSON: {"results":{"Q1":{"mark":8.5,"feedback":"Good work"},"Q2":{"mark":7.0,"feedback":"Needs improvement"}}}
```

**Grade-Only Format:**
```json
Return ONLY JSON: {"results":{"Q1":8.5,"Q2":7.0}}
```

**Mixed Format:**
```json
Return ONLY JSON: {"results":{"Q1":{"mark":9.0,"feedback":"Outstanding"},"Q2":8.5,"Q3":"Good effort"}}
```

**Compact Format:**
```json
Return ONLY JSON: {"grades":{"Q1":{"score":8,"notes":"Good"},"Q2":{"score":7,"notes":"Okay"}}}
```

**Flexible Field Names:**
The system automatically recognizes these field variations:
- **Question ID**: `question_id`, `qid`, `questionID`, `question`, `question_number`
- **Marks**: `marks_awarded`, `mark`, `score`
- **Notes**: `rubric_notes`, `feedback`, `notes`
- **Top-level keys**: `result`, `results`, `grades`, `answers`

### Question Types Supported

The system supports various assessment formats:
- **Essay Questions**: Long-form written responses
- **Short Answer**: Brief responses (1-3 sentences)
- **Mathematical Problems**: Step-by-step solutions
- **Analysis Questions**: Critical thinking and evaluation
- **Problem-Solving**: Case studies and scenarios

### File Upload Support

You can upload assessment data via:
- **JSON Files**: Structured data with questions and responses
- **CSV Files**: Tabular format with student responses
- **Text Files**: Plain text assessments

### Data Validation

The application automatically validates:
- **Question completeness**: All required fields present
- **Grade consistency**: Human grades within valid ranges
- **Response quality**: Minimum response length requirements
- **Format compliance**: JSON structure and field types

## 🆘 Troubleshooting

### Common Issues

**"API connection failed"**
- Verify your OpenRouter API key is correct
- Check your internet connection
- Ensure you have sufficient API credits

**"Model comparison not working"**
- Confirm all selected models are available in your OpenRouter plan
- Check API rate limits for high-volume testing

**"Results not saving"**
- Verify Supabase database connection
- Check storage permissions and quota

### Getting Help
- Review the [technical documentation](TECHNICAL_README.md) for detailed setup
- Check the [Issues](https://github.com/rahul-s-rajput/Swiftgrade-Testing/issues) page
- Include error logs and your configuration when reporting problems

## 🔒 Security & Privacy

- API keys are stored locally and encrypted
- Test data is stored securely in Supabase
- No data is transmitted except to authorized AI services
- Full control over data retention and deletion

---

**For technical setup and advanced configuration, see [TECHNICAL_README.md](TECHNICAL_README.md)**
