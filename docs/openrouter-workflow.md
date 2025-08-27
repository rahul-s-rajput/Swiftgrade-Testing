
# Open Router Workflow

1. **Upload Images of student tests**
2. **State \# of pages per student**
3. **Upload images of answer key**
(let me know how to make these into URL)
4. **Copy paste the question list:**
```json
[
  { "question_id": "1", "max_mark": 1 },
  { "question_id": "2", "max_mark": 1 },
  { "question_id": "3", "max_mark": 1 },
  { "question_id": "4", "max_mark": 1 },
  { "question_id": "5", "max_mark": 1 }
]
```

5. **I put the human graded list of questions not given 100%:**
```json
[
  { "question_id": "3" },
  { "question_id": "5" }
]
```

6. **Which AI models to send to (number of times)**
7. **A results page that shows by question:**
    - GROUP CLAUDE: Try 1, Try 2...
    - GROUP 5 mini: Try 1, Try 2....
8. **Statistics:**

```
--------------------------------------------------------------------------
                        Try 1              2              3           Avg.
-------------- -------------- -------------- -------------- --------------
Claude                      2              3              4              3

GPT 5                                                     
--------------------------------------------------------------------------

H: 3, 5

AI: 2, 3, 6

3 discrepancies
```


**Open R API key:**
`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`

***

## Dmitry's comments

**API application** is written using **Django**, and is responsible for handling assessment-related logic, such as uploading PDFs, storing assessment settings, and tracking the upload status.

**AI application** is written using **FastAPI**, and is responsible for communications with LLM (questions list generation, grading).

Some of the example files below contain Django or FastAPI related logic. All this can be converted to a single style using AI. These files just give the general idea of how the upload + grading flow works.

***

### Upload images of student tests

- We upload not images, but **PDFs**. This step can be omitted and done last if there is dev time, or for testing images can be uploaded.
- On FE, we use [this DHTMLX Vault library](https://docs.dhtmlx.com/vault/initialize.html). If there's no requirement on UI, Cursor can generate a simple PDF file upload form (`@simple-file-upload.html`).
- The PDF is uploaded as form data to the server. Server written using Django + DRF, accepting file as `rest_framework.serializers.FileField(required=True)`. The file is validated (can be skipped for testing).
- After uploading, file is saved to a temp folder and processed with [pdf2image](https://pypi.org/project/pdf2image/), which uses poppler-utils (see doc for install).
- Example file: `@file-upload.py`. At the end of `post` method, saving images using Django models + S3. With no Django, use `boto3`.

***

### State \# of pages per student

- On FE: simple `<input type="number"/>`.
- On BE: save number to DB in an upload-related settings table (e.g. `UploadSettings`: `assessment_id`, `pages_per_student`, `feedback_length`, etc.).
This is later sent to LLM.

***

### Upload images of answer key

- Same logic as uploading student answers.
- Can save images to a separate table, or flag in `UploadedImages` (e.g. `is_correct_answer_image: bool`). Used to distinguish student vs. answer key images.

***

### Store upload settings

- Same as in \# of pages per student.
- FE: build simple form (e.g. radio buttons).
BE: save selection in `UploadSettings` table.
Setting values influence the AI prompt.

***

### Send request to LLM

- Code responsible for request preparation shared previously.
- From API to the AI module, the following data is sent (schema below):

```python
from pydantic import BaseModel

class ImageSchema(BaseModel):
    id: int
    page_number: int
    aws_path: str

class QuestionItemSchema(BaseModel):
    question_number: str
    max_mark: float

class ImagePromptWithImagesSchema(BaseModel):
    external_assessment_id: int
    external_assessment_settings_id: int
    external_assessment_file_id: int
    pages_per_student: int
    prompt: str | None = None
    images: list[ImageSchema]
    model_assessment: list[str] | None = None
    question_list: list[QuestionItemSchema]

    class Config:
        """Prevents automatic aliasing of conflicting field names"""
        protected_namespaces = ('protected_',)
        from_attributes = True
```

- `external_assessment_id`: identifier of an assessment.
- `external_assessment_settings_id`: settings object ID (crucial for cropping images, multiple uploads possible per assessment).
- `external_assessment_file_id`: uploaded file ID.

After the request is accepted, the `create_prompt` method of [external_assessment_cases](https://drive.google.com/file/d/14J6YlhM2FDiwsFpaFBDusgAnkUZCmv5E/view?usp=sharing) is called (`@external_assessment_cases.py`).

- Data is saved to DB for later processing.
- Data is transformed to the format sent to LLM.
- Call made to image prompt service.
- Image prompt service: see [here](https://drive.google.com/file/d/1DTJtIbCTHpAGS-t1NtZY63v8TbJyRDKp/view?usp=sharing) (`@image_prompt_service(1).py`).
Batches sent in parallel, can ignore token calculation for testing.

***

### Processing AI response

- After all batch responses are returned and saved in DB, [handle response here](https://drive.google.com/file/d/1DTJtIbCTHpAGS-t1NtZY63v8TbJyRDKp/view?usp=sharing).
- Response schema ([reference](https://drive.google.com/file/d/1TGgSq-hm6caW7iQur67d3bMJoZzffAP7/view?usp=drive_link)):

```python
from pydantic import BaseModel

class ExternalAssessmentStudentAnswerSchema(BaseModel):
    question_number: str
    mark: float
    feedback: str

class ExternalAssessmentStudentResultSchema(BaseModel):
    first_name: str
    last_name: str
    answers: list[ExternalAssessmentStudentAnswerSchema]

class GPTGradingResultResponseSchema(BaseModel):
    result: list[ExternalAssessmentStudentResultSchema]
```

- The AI module maintains its own status — separate from API module status.

***

### Creating results

- After processing, create student results.
- For testing, just save data as is, avoid extra logic.
- Data levels:
    - Assessment
    - Upload
    - Student
    - Answer

Each level has a DB table. Once results are saved, you can view all student results for an assessment.


