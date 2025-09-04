# Swiftgrade AI Model Testing Assistant - Technical Guide

## 🚀 Overview

A comprehensive desktop application for testing and comparing AI model performance in grading student assessments. Built with React (frontend), FastAPI (backend), and Tauri (desktop wrapper).

## 🎯 Core Purpose

This application is designed specifically for testing and benchmarking different AI models to determine:
- **Grading accuracy** compared to human scores
- **Performance metrics** (speed, cost, consistency)
- **Model reliability** across different assessment types
- **Optimal configurations** for production use

## 📁 Project Architecture

```
project/
├── app/                    # Backend (FastAPI)
│   ├── routers/           # API endpoints for grading & testing
│   ├── schemas.py         # Pydantic models for test data
│   └── main.py           # Application entry
├── src/                    # Frontend (React + TypeScript)
│   ├── pages/            # Test session management & results
│   ├── components/       # Model comparison UI
│   └── utils/            # API client and test utilities
├── src-tauri/             # Desktop wrapper (Rust/Tauri)
├── scripts/                # Utility scripts
├── tests/                  # Test scripts for functionality
├── test_data/             # Sample assessment data for testing
└── logs/                  # Application logs
```

## 🛠️ Quick Setup for Testing

### Prerequisites
- **Python 3.8+**
- **Node.js 16+**
- **OpenRouter API key** (for multiple AI model access)
- **Supabase account** (for storing test results)

### Fast Setup
```bash
# Clone and setup
git clone <repository>
cd swiftgrade-testing-assistant

# Backend setup
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-backend.txt

# Frontend setup
npm install

# Configure environment
cp .env.example .env
# Edit .env with your OpenRouter and Supabase keys

# Start development
npm run dev
```

### Database Setup
```bash
# Run database migrations
# Execute scripts/sql/ files in Supabase SQL Editor
```

## 🔧 Configuration for Testing

### Environment Variables (.env)
```bash
# Essential for testing
OPENROUTER_API_KEY=your_key_here
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_key

# Testing configuration
OPENROUTER_DEBUG=1  # Enable detailed API logging
GRADING_MAX_CONCURRENCY=4  # Concurrent model testing
```

### Model Testing Setup
1. **API Key Configuration**: Ensure access to multiple models on OpenRouter
2. **Database Setup**: Configure Supabase for result storage
3. **Test Data**: Use sample data from `test_data/` folder
4. **Debug Mode**: Enable for detailed performance metrics

## 📊 Testing Capabilities

### Multi-Model Comparison
- **Simultaneous Testing**: Test 10+ AI models at once
- **Accuracy Metrics**: Compare AI grades vs human benchmarks
- **Performance Analysis**: Speed, cost, and consistency metrics
- **Error Pattern Analysis**: Identify systematic model weaknesses

### Supported Test Scenarios
- **Single Assessment Testing**: Test one assessment across multiple models
- **Batch Processing**: Test multiple assessments with all models
- **A/B Testing**: Compare different prompt configurations
- **Longitudinal Testing**: Track model performance over time

### Key Metrics Tracked
- **Accuracy Score**: Percentage match with human grades
- **Response Time**: API call duration per model
- **Cost Analysis**: Performance per dollar spent
- **Consistency Score**: Reliability across different assessment types
- **Error Patterns**: Common mistakes and failure modes

## 📝 API Reference

### Core Testing Endpoints

#### Test Session Management
```http
POST /sessions                    # Create new test session
GET /sessions                     # List all test sessions
GET /sessions/{id}               # Get specific test session
DELETE /sessions/{id}            # Delete test session
```

#### Model Testing
```http
POST /grade/single               # Test single assessment with selected models
POST /grade/batch                # Test multiple assessments
GET /grade/status/{task_id}      # Check testing progress
GET /grade/results/{session_id}  # Get test results
```

#### Analytics & Comparison
```http
GET /stats/{session_id}                     # Overall test statistics
GET /stats/{session_id}/model-comparison    # Model vs model comparison
GET /stats/{session_id}/accuracy-analysis   # Accuracy metrics
GET /stats/{session_id}/cost-analysis       # Cost-effectiveness analysis
```

#### Configuration
```http
GET /settings/models             # Available models for testing
PUT /settings/test-config        # Configure test parameters
GET /settings/prompt-templates   # Current prompt configurations
```

### Test Data Format
```json
{
  "session_id": "test_session_001",
  "models": ["gpt-4", "claude-3-opus", "gemini-pro"],
  "assessment_data": {
    "questions": [
      {
        "question_id": "Q1",
        "max_marks": 10,
        "description": "Essay question description"
      }
    ],
    "student_responses": {
      "student_001": {
        "Q1": "Student's written response..."
      }
    },
    "human_grades": {
      "student_001": {
        "Q1": 8.5
      }
    }
  }
}
```

## 🧪 Running Tests

### Sample Test Data
Use provided test data for quick validation:
```bash
# Test with sample data
python tests/test_with_sample_data.py

# Test specific models
python tests/test_model_comparison.py

# Performance benchmarking
python tests/test_performance_metrics.py
```

### Manual Testing Workflow
1. **Load Test Data**: Use sample assessments from `test_data/`
2. **Select Models**: Choose 2-5 models for comparison
3. **Configure Parameters**: Set grading criteria and prompts
4. **Run Tests**: Execute comparative analysis
5. **Analyze Results**: Review accuracy, speed, and cost metrics
6. **Export Reports**: Generate detailed performance reports

## 📊 Understanding Results

### Accuracy Analysis
- **Grade Match %**: How often AI matches human grades within 1 point
- **Exact Match %**: Perfect grade matches
- **Grade Distribution**: Analysis of over/under grading patterns
- **Question Type Performance**: Accuracy by assessment type

### Performance Metrics
- **Average Response Time**: Per model, per assessment
- **Cost per Assessment**: API usage costs
- **Throughput**: Assessments processed per minute
- **Reliability Score**: Consistency across test runs

### Comparative Insights
- **Model Rankings**: Best performers for different scenarios
- **Strength Analysis**: What each model excels at
- **Weakness Patterns**: Common failure modes
- **Recommendation Engine**: Suggested models for specific use cases

## 🔍 Debugging & Optimization

### Common Testing Issues
```bash
# Check API connectivity
python tests/test_api_connectivity.py

# Validate test data format
python tests/validate_test_data.py

# Monitor API usage and limits
python tests/check_api_limits.py
```

### Performance Optimization
- **Batch Processing**: Group similar assessments for efficiency
- **Model Selection**: Choose appropriate models for your use case
- **Prompt Tuning**: Optimize prompts for better accuracy
- **Caching**: Reuse results for repeated testing

### Troubleshooting
- **API Errors**: Check OpenRouter account status and limits
- **Data Format Issues**: Validate JSON structure with provided schemas
- **Performance Problems**: Monitor concurrent request limits
- **Storage Issues**: Check Supabase quota and permissions

## 🚀 Deployment for Testing

### Local Development
```bash
# Run full stack locally
npm run dev

# Run with specific test data
npm run dev -- --test-data=test_data/sample.json
```

### Production Testing
```bash
# Build desktop app
npm run tauri build

# Deploy to testing environment
# Use built binaries for comprehensive testing
```

## 📈 Best Practices for Model Testing

### Test Design
1. **Diverse Assessment Types**: Test across different subjects and formats
2. **Representative Samples**: Use real assessment data, not synthetic
3. **Statistical Significance**: Test sufficient sample sizes
4. **Blind Testing**: Don't bias results with prior knowledge

### Model Selection Strategy
- **Start Small**: Test 3-5 models initially
- **Expand Gradually**: Add more models as you identify patterns
- **Cost Consideration**: Balance accuracy needs with API costs
- **Use Case Specific**: Different models may excel in different scenarios

### Result Interpretation
- **Context Matters**: Consider the specific assessment context
- **Trend Analysis**: Look for patterns across multiple test runs
- **Practical Significance**: Focus on meaningful performance differences
- **Cost-Benefit Analysis**: Weigh accuracy improvements against costs

## 📞 Support & Resources

### Testing Resources
- [OpenRouter Model Documentation](https://openrouter.ai/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Sample Test Data](test_data/README.md)

### Getting Help
- Check existing test results in the database
- Review API logs for detailed error information
- Compare results across different test configurations
- Document and share successful testing strategies

---

**For basic usage instructions, see [README.md](README.md)**: Windows, macOS, Linux support
- **Native performance**: Rust-based with web frontend
- **Process management**: Handles backend process lifecycle
- **Security**: Sandboxed execution environment

### Database (Supabase)
- **Session storage**: Assessment sessions and configurations
- **Results storage**: Grading results and analytics
- **File storage**: Student uploads (images, documents)
- **Real-time**: Live updates for collaborative grading

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes following the established patterns
4. Add tests for new functionality
5. Update documentation as needed
6. Submit pull request

### Code Standards
- **Python**: PEP 8, type hints required
- **TypeScript**: ESLint configuration, strict mode
- **Rust**: Standard Rust formatting (`cargo fmt`)
- **Documentation**: Update relevant docs for any API changes

### Testing Requirements
- **Unit tests**: Minimum 80% coverage
- **Integration tests**: All new endpoints tested
- **E2E tests**: Critical user workflows tested
- **Cross-platform testing**: Windows, macOS, Linux

## 📊 Performance Optimization

### Backend Optimizations
- **Concurrent processing**: Multiple models graded simultaneously
- **Connection pooling**: Efficient database connections
- **Caching**: Model configurations and prompt templates
- **Batch processing**: Group similar requests

### Frontend Optimizations
- **Lazy loading**: Components loaded on demand
- **Virtual scrolling**: Large result sets handled efficiently
- **Progressive enhancement**: Core functionality works without JavaScript

### Desktop Optimizations
- **Async cleanup**: Non-blocking process termination
- **Memory management**: Efficient resource usage
- **Background processing**: Long-running tasks don't block UI

## 🔒 Security Considerations

### API Keys
- Stored locally in encrypted format
- Never transmitted except to authorized services
- Rotated regularly for security

### Data Privacy
- Student data processed locally when possible
- Cloud storage is optional
- No personal data collected without consent

### Network Security
- HTTPS-only communication
- API key validation on all requests
- Rate limiting and abuse prevention

## 📈 Monitoring & Analytics

### Application Metrics
- **Grading accuracy**: AI vs human grade comparison
- **Processing speed**: Time per assessment
- **Error rates**: Failed requests and recovery
- **Usage patterns**: Feature adoption and usage

### Performance Monitoring
- **Memory usage**: Track resource consumption
- **API latency**: Monitor external service performance
- **Database performance**: Query optimization and indexing

## 🆘 Troubleshooting

### Common Development Issues

**Backend won't start**
```bash
# Check Python version
python --version

# Verify dependencies
pip list | grep fastapi

# Check environment variables
cat .env
```

**Frontend build fails**
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Check TypeScript errors
npm run type-check
```

**Tauri build issues**
```bash
# Update Rust
rustup update

# Clean build cache
npm run tauri build -- --no-bundle
```

**Database connection issues**
- Verify Supabase credentials
- Check network connectivity
- Review Supabase project status

## 📚 Additional Resources

### External Documentation
- [OpenRouter API](https://openrouter.ai/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Tauri Documentation](https://tauri.app/v1/guides/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

### Internal Documentation
- [API JSON Formats](docs/API_JSON_FORMATS.md)
- [Reasoning Implementation](docs/REASONING_IMPLEMENTATION.md)
- [Frontend Input Formats](docs/FRONTEND_INPUT_JSON.md)
- [Test Inputs Guide](docs/TEST_INPUTS_README.md)

## 📞 Support

For technical issues and development questions:
- Create an issue on GitHub
- Include detailed error messages and reproduction steps
- Specify your development environment (OS, versions, etc.)
- Attach relevant log files when possible

---

**For end users and installation instructions, see [README.md](README.md)**
