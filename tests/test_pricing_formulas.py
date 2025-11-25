"""
Testes unitários para o módulo pricing_formulas.py
"""
import unittest
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.pricing_formulas import PricingFormula


class TestPricingFormula(unittest.TestCase):
    """Testes para fórmulas de precificação."""
    
    def test_calculate_pp_fob_usd_version_1_0(self):
        """Testa cálculo com versão 1.0."""
        wti = 70.0
        result = PricingFormula.calculate_pp_fob_usd(wti, formula_version="1.0")
        
        expected = (wti * 0.014) + 0.35
        self.assertAlmostEqual(result, expected, places=4)
    
    def test_calculate_pp_fob_usd_version_1_1(self):
        """Testa cálculo com versão 1.1."""
        wti = 70.0
        result = PricingFormula.calculate_pp_fob_usd(wti, formula_version="1.1")
        
        expected = (wti * 0.0145) + 0.32
        self.assertAlmostEqual(result, expected, places=4)
    
    def test_calculate_pp_fob_usd_version_1_2(self):
        """Testa cálculo com versão 1.2 (atual)."""
        wti = 70.0
        result = PricingFormula.calculate_pp_fob_usd(wti, formula_version="1.2")
        
        expected = (wti * 0.014) + 0.35 + (wti * 0.0001)
        self.assertAlmostEqual(result, expected, places=4)
    
    def test_calculate_pp_fob_usd_current_version(self):
        """Testa cálculo com versão atual (None)."""
        wti = 70.0
        result = PricingFormula.calculate_pp_fob_usd(wti)
        
        # Deve usar versão atual (1.2)
        expected = (wti * 0.014) + 0.35 + (wti * 0.0001)
        self.assertAlmostEqual(result, expected, places=4)
    
    def test_calculate_pp_fob_usd_invalid_version(self):
        """Testa versão inválida."""
        wti = 70.0
        
        with self.assertRaises(ValueError):
            PricingFormula.calculate_pp_fob_usd(wti, formula_version="2.0")
    
    def test_calculate_pp_fob_usd_invalid_wti(self):
        """Testa WTI inválido."""
        with self.assertRaises(ValueError):
            PricingFormula.calculate_pp_fob_usd(-10)
        
        with self.assertRaises(ValueError):
            PricingFormula.calculate_pp_fob_usd(0)
    
    def test_get_formula_metadata(self):
        """Testa obtenção de metadados."""
        metadata = PricingFormula.get_formula_metadata("1.0")
        
        self.assertIn('author', metadata)
        self.assertIn('date', metadata)
        self.assertIn('formula', metadata)
        self.assertIn('description', metadata)
    
    def test_get_formula_metadata_current(self):
        """Testa metadados da versão atual."""
        metadata = PricingFormula.get_formula_metadata()
        
        self.assertIn('author', metadata)
        self.assertIn('date', metadata)
    
    def test_list_available_versions(self):
        """Testa listagem de versões."""
        versions = PricingFormula.list_available_versions()
        
        self.assertIn("1.0", versions)
        self.assertIn("1.1", versions)
        self.assertIn("1.2", versions)
    
    def test_get_current_version(self):
        """Testa obtenção da versão atual."""
        version = PricingFormula.get_current_version()
        
        self.assertEqual(version, "1.2")


if __name__ == '__main__':
    unittest.main()

