# Project Health Reporting Agent

## Overview

The Project Health Reporting Agent is an AI-assisted project analytics system designed to evaluate project health from project plan workbooks and generate executive-ready reports.

The solution combines deterministic project health scoring with LLM-generated explanations to provide transparent, explainable, and auditable project assessments. The system analyzes project schedules, milestones, task variances, critical-path activities, and stakeholder comments to determine project health and produce portfolio-level reporting.

---

## Key Capabilities

- Automated project health assessment (Green / Amber / Red)
- Schedule and milestone analysis
- Risk extraction from stakeholder comments
- Deterministic and explainable scoring framework
- Executive narrative generation using LLMs
- Portfolio-level trend identification
- Emerging risk detection across projects
- Automated PowerPoint report generation

---

## Architecture
<img width="2816" height="1536" alt="architectural_diagram" src="https://github.com/user-attachments/assets/244d3653-899b-4875-b60a-3f5578b7b10e" />


---

## Core Design Principle

### Deterministic Scoring, AI-Assisted Explanation

The system intentionally separates project health assessment from narrative generation.

```text
Deterministic Scoring
        ↓
     Project RAG

LLM
        ↓
 Explanation Only
```

Project health (Green / Amber / Red) is determined exclusively through algorithmic scoring rules and weighted project indicators.

The LLM is used only to generate executive-friendly explanations and summarize identified risks.

This approach improves:

- Transparency
- Auditability
- Consistency
- Explainability
- Enterprise trustworthiness

---

## Methodology

### 1. Data Extraction

Project plans are parsed from Excel workbooks and normalized into a structured representation.

### 2. Feature Engineering

The system derives project health indicators including:

- Schedule slippage
- Variance health
- Overdue task ratio
- Milestone health
- Blocker density
- Schedule health signals
- Comment risk signals
- Data quality metrics

### 3. Comment Risk Analysis

Stakeholder comments are analyzed to identify:

- Delivery risks
- Root causes
- Dependency concerns
- Escalations
- Potential blockers

### 4. Deterministic Health Scoring

Project health is determined using weighted signals and rule-based overrides.

Scoring outputs include:

- RAG status
- Confidence score
- Data quality score
- Supporting evidence

### 5. Executive Insight Generation

Project indicators are translated into:

- Positive drivers
- Negative drivers
- Review flags
- Portfolio risks

### 6. Portfolio Reporting

Project-level outputs are aggregated to generate:

- Executive summaries
- Portfolio health views
- Emerging risk assessments
- Cross-project trend analysis
- Executive recommendations

---

## Project Structure

```text
project-health-reporting-agent/
│
├── data/
│   ├── S2P_Project.xlsx
│   ├── Project_Plan_B.xlsx
│
├── reports/
│   ├── weekly/
│   └── executive_project_health_report.pptx
│
├── src/
│   ├── parser.py
│   ├── features.py
│   ├── comment_analyzer.py
│   ├── scorer.py
│   ├── insights.py
│   ├── prompt.py
│   ├── narrator.py
│   ├── runner.py
│   └── presentation.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Installation

```bash
git clone <repository-url>

cd project-health-reporting-agent

pip install -r requirements.txt
```

Create a `.env` file:

```env
GEMINI_API_KEY=your_api_key_here
```

---

## Running the Project

### Data
The data was not pushed to GitHub to maintain privacy. Create a folder 'data' in root directory and place the excel files 'Project_Plan_B.xlsx' and 'S2P_Project.xlsx' inside it.
Folder 'pseudo_data_check' contains a fake excel project plan with synthetic data just for testing purposes. This data can be used as well for testing purposes.

### Generate Project Health Reports

```bash
python src/runner.py
```

This produces project-level health reports in:

```text
reports/weekly/
```

### Generate Executive Presentation

```bash
python src/presentation.py
```

This generates:

```text
reports/executive_project_health_report.pptx
```

---

## Outputs

### Project Health Reports

Generated as structured JSON outputs containing:

- Project health classification
- Feature metrics
- Confidence scores
- Data quality assessments
- Executive insights
- Narrative explanations

### Executive Presentation

The generated PowerPoint includes:

- Executive Summary
- Cross-Project Trends
- Emerging Portfolio Risks
- Projects Requiring Attention
- Executive Recommendations
- Portfolio Dashboard
- Methodology & Confidence

---

## Technologies Used

- Python
- Pandas
- OpenPyXL
- Pydantic
- Google Gemini
- python-pptx

---

## Future Extensions

Potential enhancements include:

- Automated scheduling and orchestration
- Dashboard integration
- Historical trend tracking
- Primavera / MS Project connectors
- Email-based executive distribution
- Multi-project portfolio monitoring

---

## Author
Dhruv Patel
