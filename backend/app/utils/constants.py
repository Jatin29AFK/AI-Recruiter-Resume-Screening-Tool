from os import getenv

# When true, scoring and ATS penalties are softened to be more permissive.
LENIENT_MODE = getenv("LENIENT_MODE", "false").lower() in ("1", "true", "yes")
DOMAIN_SKILL_PACKS = {
    "software_web": {
        "label": "Software / Web",
        "keywords": [
            "software engineer", "frontend", "backend", "full stack", "web developer",
            "react", "node.js", "express", "rest api", "typescript", "javascript",
            "sql", "database", "api", "web application"
        ],
        "categories": {
            "programming_languages": [
                "python", "java", "go", "rust", "c", "c++", "c#", "javascript", "typescript", "sql"
            ],
            "frameworks_and_web": [
                "react", "node.js", "nodejs", "express", "fastapi", "flask", "django",
                "bootstrap", "tailwind", "rest api", "restful api", "api development",
                "nestjs", "spring boot", "falcon"
            ],
            "databases": [
                "postgresql", "mysql", "mongodb", "sqlite", "redis"
            ],
            "cloud_devops_tools": [
                "git", "github", "docker", "kubernetes", "aws", "azure", "gcp",
                "linux", "bash"
            ],
        },
        "aliases": {
            "nodejs": "node.js",
            "node js": "node.js",
            "node-js": "node.js",
            "restful api": "rest api",
            "js": "javascript",
            "java script": "javascript",
            "java-script": "javascript",
            "type script": "typescript",
            "type-script": "typescript",
            "nest js": "nestjs",
            "nest.js": "nestjs",
            "springboot": "spring boot",
            "spring-boot": "spring boot",
            "ts": "typescript",
        },
    },

    "ai_ml_data": {
        "label": "AI / ML / Data",
        "keywords": [
            "machine learning", "deep learning", "nlp", "computer vision",
            "data scientist", "data analysis", "transformers", "llm", "rag",
            "langchain", "pytorch", "tensorflow", "scikit-learn",
            "fastapi", "resume parsing", "semantic similarity", "text preprocessing",
            "generative ai", "gemini", "scoring system", "ats", "resume intelligence"
        ],
        "categories": {
            "data_ai_ml": [
                "machine learning", "deep learning", "nlp", "natural language processing",
                "computer vision", "data analysis", "data science", "pandas", "numpy",
                "scikit-learn", "sklearn", "tensorflow", "pytorch", "keras",
                "transformers", "llm", "rag", "langchain", "langgraph",
                "sentence transformers", "spacy", "hugging face", "faiss", "chroma",
                "vector database", "opencv", "prompt engineering",
                "text preprocessing", "semantic similarity", "text classification",
                "skill extraction", "resume parsing", "generative ai",
                "gemini", "llm integration", "scoring system", "scoring systems",
                "evidence validation", "gap detection", "explainable ai",
                "evaluation metrics", "tfidf", "tf-idf", "cosine similarity",
                "ats", "keyword extraction", "information extraction"
            ],
            "programming_languages": [
                "python", "sql"
            ],
            "frameworks_and_apis": [
                "fastapi", "flask", "django", "rest api", "rest apis", "restful api",
                "json", "json/data handling", "json data handling",
                "react", "tailwind css", "tailwind"
            ],
            "cloud_devops_tools": [
                "git", "github", "docker", "aws", "azure", "gcp",
                "vercel", "render", "deployment"
            ],
        },
        "aliases": {
            "sklearn": "scikit-learn",
            "natural language processing": "nlp",
            "llms": "llm",
            "large language models": "llm",
            "restful api": "rest api",
            "rest apis": "rest api",
            "json/data handling": "json",
            "json data handling": "json",
            "llm integration": "llm",
            "gemini api": "gemini",
            "tf-idf": "tfidf",
        },
    },

    "mechanical_simulation": {
        "label": "Mechanical / Simulation / CFD",
        "keywords": [
            "cfd", "thermal", "fluid mechanics", "heat transfer", "simulation",
            "conjugate heat transfer", "electronics cooling", "ansys", "fluent",
            "thermal analysis", "flow analysis", "switchgear", "transformer"
        ],
        "categories": {
            "simulation_cae_mechanical": [
                "cfd", "thermal analysis", "flow analysis", "fluid mechanics",
                "heat transfer", "conjugate heat transfer", "electronics cooling",
                "simulation", "simulation tools", "digital prototypes",
                "thermal performance prediction", "analysis models",
                "switchgear", "ups", "transformer", "ansys", "ansys fluent",
                "icem cfd", "star-ccm+", "fea", "finite element analysis",
                "cad", "solidworks", "catia", "creo", "dfss"
            ]
        },
        "aliases": {
            "computational fluid dynamics": "cfd",
            "thermal": "thermal analysis",
            "finite element analysis": "fea",
        },
    },

    "electrical_embedded": {
        "label": "Electrical / Embedded",
        "keywords": [
            "embedded", "firmware", "microcontroller", "pcb", "electronics",
            "plc", "scada", "rtos", "electrical design", "control systems"
        ],
        "categories": {
            "electrical_embedded": [
                "embedded c", "firmware", "microcontroller", "pcb", "circuit design",
                "electronics", "plc", "scada", "rtos", "uart", "spi", "i2c",
                "verilog", "vhdl", "matlab", "simulink"
            ]
        },
        "aliases": {
            "embedded systems": "firmware",
        },
    },
}


def get_domain_label(domain_name: str) -> str:
    pack = DOMAIN_SKILL_PACKS.get(domain_name)
    return pack["label"] if pack else "General"


def merge_all_categories() -> dict:
    merged = {}
    for pack in DOMAIN_SKILL_PACKS.values():
        for category, skills in pack["categories"].items():
            merged.setdefault(category, [])
            merged[category].extend(skills)

    for category in merged:
        merged[category] = sorted(set(merged[category]))

    return merged


def merge_all_aliases() -> dict:
    merged = {}
    for pack in DOMAIN_SKILL_PACKS.values():
        merged.update(pack["aliases"])
    return merged


SKILL_CATEGORIES = merge_all_categories()
SKILL_ALIASES = merge_all_aliases()