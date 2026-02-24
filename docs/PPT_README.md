# Project Presentation (PowerPoint)

## Generate the Presentation

To generate the ~30-slide PowerPoint for your professor:

```bash
# Install dependencies (if not already installed)
pip install python-pptx matplotlib

# Run the script
python scripts/generate_project_ppt.py
```

**Output:** `docs/Multi-Agent_Powerplant_Project.pptx`

## Contents

The presentation includes:

1. **Title** – Multi-Agent Powerplant Monitoring System
2. **Outline** – Presentation structure
3. **Why This Project?** – Motivation for choosing this topic
4. **Importance & Motivation** – Industrial IoT, early detection, RCA
5. **Problems We Solve** – Real-time detection, interpretability, automation
6. **Key Challenges** – Latency, explainability, scalability
7. **Problem Domain** – Industrial IoT context
8. **Our Approach** – Multi-agent pipeline
9. **System Architecture** – With diagram
10. **Architecture Diagram** – Visual overview
11. **Agent A: Monitor** – Anomaly detection
12. **Agent B: Diagnosis** – Root cause analysis
13. **Agent C: Ticket** – Ticket creation
14. **Agent D: Review** – Human review interface
15. **Data Flow** – With diagram
16. **MQTT Message Bus** – Pub/sub design
17. **Simulator & Fault Injection** – Scenario-driven testing
18. **Supported Fault Types** – bearing_wear, clogging, etc.
19. **Agent D Dashboard** – With mockup
20. **Troubleshooting Rules & RAG** – Rules creation, vector search
21. **Salesforce Integration** – Case creation on approve
22. **Technology Stack** – Python, FastAPI, React, etc.
23. **Demo Flow** – Step-by-step
24. **Human-in-the-Loop** – Design rationale
25. **Key Benefits** – Summary
26. **Evaluation & Metrics** – Planned metrics
27. **Lessons Learned** – Takeaways
28. **Future Work** – Next steps
29. **Conclusion** – Summary
30. **Q & A** – Thank you

## Diagrams

The script generates three PNG images in `docs/ppt_images/`:

- `architecture.png` – System architecture (Simulator + MQTT + 4 agents)
- `data_flow.png` – Data flow (Telemetry → Alerts → Diagnosis → Ticket → Feedback)
- `dashboard.png` – Dashboard UI mockup

These are embedded in the presentation.
