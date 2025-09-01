# Test Grading App - Test Input Instructions

## Files Created

1. **Student Test Paper (HTML)**: `student-test-pages.html`
   - 4-page student exam with handwritten-style answers
   - Shows Sarah Johnson's responses to 10 questions (Score: 94/100)
   - Includes mathematical work, diagrams, and written explanations

1b. **Alternative Student Test (HTML)**: `student-test-pages-alt.html`
   - 4-page exam from Michael Chen (Score: 69/100)
   - Contains more errors and rushed work
   - Good for testing AI's ability to identify mistakes

2. **Answer Key (HTML)**: `answer-key-pages.html`
   - 4-page answer key with marking scheme
   - Contains correct answers and step-by-step solutions
   - Includes detailed marking breakdown for each question

3. **Question List**: `test_inputs_questions.txt`
   - List of all 10 questions with IDs (Q1-Q10)
   - Shows maximum marks for each question
   - Total: 100 marks

4. **Human Grades**: `test_inputs_human_grades.txt`
   - Detailed human grading for Sarah Johnson
   - Includes feedback and comments
   - Total score: 94/100 (Grade A)

4b. **Alternative Human Grades**: `test_inputs_human_grades_alt.txt`
   - Detailed grading for Michael Chen
   - Shows C+ level work (69/100)
   - More critical feedback

5. **Configuration JSON**: `test_configuration.json`
   - Complete test configuration in JSON format
   - Can be used for programmatic input

## How to Use These Files

### Converting HTML to Images

1. **Method 1: Browser Screenshot**
   - Open the HTML files in a browser
   - Use browser's print preview (Ctrl+P)
   - Save as PDF, then convert to JPG
   - Or use full-page screenshot extensions

2. **Method 2: Online Converters**
   - Use online HTML to Image converters
   - Upload the HTML files
   - Download as JPG/PNG

3. **Method 3: Programmatic (Python)**
   ```python
   from selenium import webdriver
   from PIL import Image
   
   driver = webdriver.Chrome()
   driver.get('file:///path/to/html')
   driver.save_screenshot('output.png')
   ```

### Input Format for the App

When using the NewAssessment page:

1. **Assessment Name**: 
   "Mathematics & Science Midterm - Fall 2024"

2. **Student Images**: 
   Upload the 4 converted JPG files from student HTML

3. **Answer Key Images**: 
   Upload the 4 converted JPG files from answer key HTML

4. **Question List** (paste this):
   ```
   Q1: Differentiate f(x) = 3x³ - 2x² + 5x - 7 (10 marks)
   Q2: Solve the integral ∫(2x² + 3x - 1)dx (15 marks)
   Q3: Explain photosynthesis and write chemical equation (12 marks)
   Q4: Calculate area of circle with radius r = 7.5 cm (8 marks)
   Q5: Balance chemical equation Fe + O₂ → Fe₂O₃ (10 marks)
   Q6: Ball thrown upward - find max height and time (15 marks)
   Q7: Describe atomic structure, atomic number, mass number (10 marks)
   Q8: Find roots of x² - 5x + 6 = 0 (8 marks)
   Q9: Convert 75°F to Celsius and Kelvin (7 marks)
   Q10: State Newton's Second Law and mathematical form (5 marks)
   ```

5. **Human Graded Marks** (paste this):
   ```
   Q1: 10/10 - Perfect application of power rule
   Q2: 14/15 - Minor formatting issue in final answer
   Q3: 11/12 - Missing detail about light/dark reactions
   Q4: 8/8 - Correct formula and calculation
   Q5: 10/10 - Perfectly balanced equation
   Q6: 13/15 - Small rounding error in final height
   Q7: 9/10 - Diagram could be more detailed
   Q8: 8/8 - Correct factorization method
   Q9: 6/7 - Small rounding inconsistency
   Q10: 5/5 - Perfect statement of Newton's Second Law
   ```

6. **AI Models**: Select multiple models for comparison

7. **Iterations**: Set to 3 for consistent testing

## Test Scenarios

This test data includes:
- **Easy Questions**: Q1, Q4, Q8, Q9, Q10 (basic calculations)
- **Medium Questions**: Q2, Q3, Q5, Q7 (conceptual + calculations)
- **Hard Questions**: Q6 (multi-step physics problem)

### Two Student Profiles:
1. **Sarah Johnson** (94/100 - Grade A)
   - Strong student with minor errors
   - Clear presentation and methodology
   - Good for testing AI's ability to recognize excellence

2. **Michael Chen** (69/100 - Grade C+)
   - Average student with multiple errors
   - Rushed work, calculation mistakes
   - Good for testing AI's error detection and partial credit

## Expected Results

The AI grading should be compared against:
- **Total Human Score**: 94/100
- **Individual Question Scores**: As listed in human grades
- **Key Evaluation Points**:
  - Mathematical accuracy
  - Step-by-step reasoning
  - Proper use of formulas
  - Conceptual understanding
  - Presentation quality

## Notes

- The student answers include intentional minor errors to test AI detection
- The answer key provides comprehensive marking schemes
- Human grades include detailed feedback for comparison
- Test covers both STEM calculation and conceptual questions