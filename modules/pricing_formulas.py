"""
Módulo de Fórmulas de Precificação - Configuração centralizada
Gerencia fórmulas de cálculo de preços com versionamento.
"""
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PricingFormula:
    """
    Classe para gerenciar fórmulas de precificação com versionamento.
    """
    
    # Versão atual da fórmula
    CURRENT_VERSION = "1.2"
    
    @staticmethod
    def calculate_pp_fob_usd(wti: float, formula_version: Optional[str] = None) -> float:
        """
        Calcula PP_FOB_USD baseado em WTI.
        
        Args:
            wti: Preço do WTI em USD
            formula_version: Versão da fórmula a usar (None = versão atual)
            
        Returns:
            PP_FOB_USD calculado
            
        Raises:
            ValueError: Se versão inválida ou WTI inválido
        """
        if wti <= 0 or not isinstance(wti, (int, float)):
            raise ValueError(f"WTI deve ser um número positivo, recebido: {wti}")
        
        version = formula_version or PricingFormula.CURRENT_VERSION
        
        if version == "1.0":
            # Fórmula original
            return (wti * 0.014) + 0.35
        elif version == "1.1":
            # Versão ajustada (coeficiente maior, spread menor)
            return (wti * 0.0145) + 0.32
        elif version == "1.2":
            # Versão atual (com ajuste não-linear)
            return (wti * 0.014) + 0.35 + (wti * 0.0001)
        else:
            raise ValueError(f"Versão de fórmula inválida: {version}. Disponíveis: 1.0, 1.1, 1.2")
    
    @staticmethod
    def get_formula_metadata(version: Optional[str] = None) -> Dict:
        """
        Retorna metadados da fórmula (autor, data, validação).
        
        Args:
            version: Versão da fórmula (None = versão atual)
            
        Returns:
            Dict com metadados
        """
        version = version or PricingFormula.CURRENT_VERSION
        
        metadata = {
            "1.0": {
                "author": "Initial",
                "date": "2024-01-01",
                "validation": "backtest_2023",
                "formula": "PP_FOB_USD = (WTI * 0.014) + 0.35",
                "description": "Fórmula inicial baseada em análise histórica"
            },
            "1.1": {
                "author": "Data Team",
                "date": "2024-06-01",
                "validation": "backtest_2024_q1",
                "formula": "PP_FOB_USD = (WTI * 0.0145) + 0.32",
                "description": "Ajuste de coeficiente e spread baseado em Q1 2024"
            },
            "1.2": {
                "author": "Data Team",
                "date": "2024-12-01",
                "validation": "backtest_2024_q3",
                "formula": "PP_FOB_USD = (WTI * 0.014) + 0.35 + (WTI * 0.0001)",
                "description": "Versão atual com ajuste não-linear para alta volatilidade"
            }
        }
        
        return metadata.get(version, {})
    
    @staticmethod
    def list_available_versions() -> list:
        """
        Lista todas as versões disponíveis.
        
        Returns:
            Lista de versões disponíveis
        """
        return ["1.0", "1.1", "1.2"]
    
    @staticmethod
    def get_current_version() -> str:
        """
        Retorna versão atual da fórmula.
        
        Returns:
            String com versão atual
        """
        return PricingFormula.CURRENT_VERSION

