def get_flow_definition() -> dict:
    return {
        "perceive": [
            {"mode": "parallel", "tasks": ["validate_file_path", "detect_pdf_type"]},
        ],
        "plan": [
            {"mode": "sequential", "tasks": ["select_parsing_strategy", "prepare_extraction_config"]},
        ],
        "act": [
            {"mode": "sequential", "tasks": ["extract_content", "structure_output"]},
        ],
    }