"""
Testes unitários para o módulo data_engine.py
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.data_engine import (
    validate_market_data,
    calculate_data_quality_metrics,
    calculate_price_confidence,
    sensitivity_analysis,
    calculate_cost_buildup,
    DataValidationError
)


class TestDataValidation(unittest.TestCase):
    """Testes para validação de dados."""
    
    def setUp(self):
        """Prepara dados de teste."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        self.valid_df = pd.DataFrame({
            'wti': np.random.uniform(60, 90, 30),
            'usd_brl': np.random.uniform(4.5, 5.5, 30),
            'pp_fob_usd': np.random.uniform(1.0, 1.5, 30),
            'date': dates
        })
    
    def test_validate_market_data_valid(self):
        """Testa validação com dados válidos."""
        df_validated, warnings = validate_market_data(self.valid_df)
        
        self.assertFalse(df_validated.empty)
        self.assertIn('wti', df_validated.columns)
        self.assertIn('usd_brl', df_validated.columns)
        self.assertIn('pp_fob_usd', df_validated.columns)
    
    def test_validate_market_data_empty(self):
        """Testa validação com DataFrame vazio."""
        empty_df = pd.DataFrame()
        
        with self.assertRaises(DataValidationError):
            validate_market_data(empty_df)
    
    def test_validate_market_data_missing_columns(self):
        """Testa validação com colunas faltando."""
        incomplete_df = pd.DataFrame({
            'wti': [70.0],
            'date': [datetime.now()]
        })
        
        with self.assertRaises(DataValidationError):
            validate_market_data(incomplete_df)
    
    def test_validate_market_data_outliers(self):
        """Testa detecção de outliers."""
        # Adiciona outliers extremos
        df_with_outliers = self.valid_df.copy()
        df_with_outliers.loc[0, 'wti'] = 500.0  # Outlier extremo
        df_with_outliers.loc[1, 'usd_brl'] = 20.0  # Outlier extremo
        
        df_validated, warnings = validate_market_data(df_with_outliers)
        
        # Deve detectar outliers
        self.assertTrue(any('outliers' in w.lower() for w in warnings))


class TestDataQualityMetrics(unittest.TestCase):
    """Testes para métricas de qualidade de dados."""
    
    def setUp(self):
        """Prepara dados de teste."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        self.test_df = pd.DataFrame({
            'wti': np.random.uniform(60, 90, 30),
            'usd_brl': np.random.uniform(4.5, 5.5, 30),
            'pp_fob_usd': np.random.uniform(1.0, 1.5, 30),
            'date': dates
        })
        self.test_df = self.test_df.set_index('date')
    
    def test_calculate_data_quality_metrics(self):
        """Testa cálculo de métricas de qualidade."""
        metrics = calculate_data_quality_metrics(self.test_df)
        
        self.assertIn('completeness', metrics)
        self.assertIn('duplicates', metrics)
        self.assertIn('date_range', metrics)
        self.assertIn('outliers_count', metrics)
        
        self.assertGreaterEqual(metrics['completeness'], 0.0)
        self.assertLessEqual(metrics['completeness'], 1.0)
    
    def test_calculate_data_quality_metrics_empty(self):
        """Testa métricas com DataFrame vazio."""
        empty_df = pd.DataFrame()
        metrics = calculate_data_quality_metrics(empty_df)
        
        self.assertEqual(metrics['completeness'], 0.0)
        self.assertEqual(metrics['duplicates'], 0)


class TestPriceConfidence(unittest.TestCase):
    """Testes para métricas de confiança."""
    
    def setUp(self):
        """Prepara dados de teste."""
        dates = pd.date_range(start=datetime.now() - timedelta(days=30), periods=30, freq='D')
        self.test_df = pd.DataFrame({
            'WTI': np.random.uniform(60, 90, 30),
            'USD_BRL': np.random.uniform(4.5, 5.5, 30),
            'PP_FOB_USD': np.random.uniform(1.0, 1.5, 30),
            'PP_Price': np.random.uniform(8.0, 12.0, 30)
        }, index=dates)
    
    def test_calculate_price_confidence(self):
        """Testa cálculo de confiança."""
        current_price = 10.0
        confidence = calculate_price_confidence(self.test_df, current_price)
        
        self.assertIn('confidence_score', confidence)
        self.assertIn('data_freshness_days', confidence)
        self.assertIn('data_completeness', confidence)
        self.assertIn('recommendation', confidence)
        
        self.assertGreaterEqual(confidence['confidence_score'], 0.0)
        self.assertLessEqual(confidence['confidence_score'], 1.0)
    
    def test_calculate_price_confidence_empty(self):
        """Testa confiança com DataFrame vazio."""
        empty_df = pd.DataFrame()
        confidence = calculate_price_confidence(empty_df, 10.0)
        
        self.assertEqual(confidence['confidence_score'], 0.0)
        self.assertIn('Dados insuficientes', confidence['recommendation'])


class TestSensitivityAnalysis(unittest.TestCase):
    """Testes para análise de sensibilidade."""
    
    def setUp(self):
        """Prepara dados de teste."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        self.test_df = pd.DataFrame({
            'WTI': np.random.uniform(60, 90, 30),
            'USD_BRL': np.random.uniform(4.5, 5.5, 30),
            'PP_FOB_USD': np.random.uniform(1.0, 1.5, 30)
        }, index=dates)
    
    def test_sensitivity_analysis(self):
        """Testa análise de sensibilidade."""
        base_params = {
            'ocean_freight': 60,
            'freight_internal': 0.15,
            'icms': 18,
            'margin': 10
        }
        
        ranges = {
            'ocean_freight': (-10, +10),
            'icms': (-2, +2),
            'margin': (-2, +2)
        }
        
        # Mock get_market_data para retornar dados de teste
        import modules.data_engine as de
        original_get_market_data = de.get_market_data
        
        def mock_get_market_data(days_back=180, validate=True):
            return self.test_df
        
        de.get_market_data = mock_get_market_data
        
        try:
            result = sensitivity_analysis(base_params, ranges, days_back=30)
            
            # Verifica se retornou DataFrame
            self.assertIsInstance(result, pd.DataFrame)
            
            if not result.empty:
                self.assertIn('parameter', result.columns)
                self.assertIn('price_impact', result.columns)
                self.assertIn('price_impact_pct', result.columns)
        finally:
            # Restaura função original
            de.get_market_data = original_get_market_data


class TestCostBuildup(unittest.TestCase):
    """Testes para cálculo de buildup de custo."""
    
    def setUp(self):
        """Prepara dados de teste."""
        dates = pd.date_range(start='2024-01-01', periods=30, freq='D')
        self.test_df = pd.DataFrame({
            'WTI': np.random.uniform(60, 90, 30),
            'USD_BRL': np.random.uniform(4.5, 5.5, 30),
            'PP_FOB_USD': np.random.uniform(1.0, 1.5, 30)
        }, index=dates)
    
    def test_calculate_cost_buildup(self):
        """Testa cálculo de buildup."""
        result = calculate_cost_buildup(
            self.test_df,
            ocean_freight=60,
            freight_internal=0.15,
            icms_pct=18,
            margin_pct=10
        )
        
        self.assertFalse(result.empty)
        self.assertIn('CFR_USD', result.columns)
        self.assertIn('Landed_BRL', result.columns)
        self.assertIn('Operational_Cost', result.columns)
        self.assertIn('Price_Net', result.columns)
        self.assertIn('PP_Price', result.columns)
        self.assertIn('Trend', result.columns)
        
        # Verifica que PP_Price é positivo
        self.assertTrue((result['PP_Price'] > 0).all())
    
    def test_calculate_cost_buildup_empty(self):
        """Testa buildup com DataFrame vazio."""
        empty_df = pd.DataFrame()
        result = calculate_cost_buildup(
            empty_df,
            ocean_freight=60,
            freight_internal=0.15,
            icms_pct=18,
            margin_pct=10
        )
        
        self.assertTrue(result.empty)
    
    def test_calculate_cost_buildup_missing_columns(self):
        """Testa buildup com colunas faltando."""
        incomplete_df = pd.DataFrame({
            'WTI': [70.0]
        })
        
        with self.assertRaises(ValueError):
            calculate_cost_buildup(
                incomplete_df,
                ocean_freight=60,
                freight_internal=0.15,
                icms_pct=18,
                margin_pct=10
            )


if __name__ == '__main__':
    unittest.main()

