from typing import List, Dict, Tuple, Optional
import json
import numpy as np
# Alias de tipo para clareza
Centro = Tuple[float, float]

# A estrutura de dados principal
CalibrationDatabase = Dict[
    str,  # -> label (e.g., "carteira_oab")
    Dict[
        str,  # -> key (e.g., "nome", "inscricao")
        Dict[
            str,  # -> "centers" ou "mean_center"
            List[Centro] | Optional[Centro] 
        ]
    ]
]

def initialize_db(schema: Dict[str, str], label: str, db: CalibrationDatabase) -> None:
    """Inicializa a estrutura para um novo label e schema."""
    if label not in db:
        db[label] = {}
    
    for key in schema.keys():
        if key not in db[label]:
            db[label][key] = {
                "centers": [],
                "mean_center": None
            }

def update_db_with_llm_result(label: str, key: str, new_center: Centro, db: CalibrationDatabase) -> None:
    """Atualiza o histórico e recalcula a média após uma chamada LLM."""
    
    # Adiciona o novo centro ao histórico
    db[label][key]["centers"].append(new_center)
    
    # Recalcula o mean-center (tomando a média)
    centers_history = db[label][key]["centers"]
    
    if centers_history:
        
        # Converte para array numpy para calcular a média
        np_centers = np.array(centers_history)
        mean_x = np.mean(np_centers[:, 0])
        mean_y = np.mean(np_centers[:, 1])
        db[label][key]["mean_center"] = (mean_x, mean_y)
    else:
        db[label][key]["mean_center"] = None

# ----------------------------------------------------
# Demonstração
# ----------------------------------------------------

# 1. Inicializa o banco de dados (vazio)
CALIBRATION_DB: CalibrationDatabase = {}

SCHEMA = {"nome": "string", "inscricao": "string"}
LABEL = "carteira_oab"

initialize_db(SCHEMA, LABEL, CALIBRATION_DB)

print("--- DB Inicializado ---")
print(json.dumps(CALIBRATION_DB, indent=2))

# 2. Processa a 1ª Amostra com LLM
center_sample_1 = (100.5, 50.1) # LLM retornou este centro para 'nome'
update_db_with_llm_result(LABEL, "nome", center_sample_1, CALIBRATION_DB)

print("\n--- Após 1ª Amostra (LLM) ---")
print(json.dumps(CALIBRATION_DB, indent=2))

# 3. Processa a 2ª Amostra com LLM
center_sample_2 = (105.5, 55.1) # LLM retornou um centro ligeiramente diferente
update_db_with_llm_result(LABEL, "nome", center_sample_2, CALIBRATION_DB)

print("\n--- Após 2ª Amostra (LLM) ---")
print(json.dumps(CALIBRATION_DB, indent=2))