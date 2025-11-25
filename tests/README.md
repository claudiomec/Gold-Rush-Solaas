# Testes Unitários - Gold Rush SAAS

Este diretório contém testes unitários para os módulos principais do sistema.

## Estrutura

- `test_data_engine.py` - Testes para o módulo de engine de dados
- `test_database.py` - Testes para o módulo de database
- `test_pricing_formulas.py` - Testes para fórmulas de precificação

## Como Executar

### Executar todos os testes

```bash
python -m pytest tests/ -v
```

ou

```bash
python -m unittest discover tests -v
```

### Executar testes específicos

```bash
# Apenas testes do data_engine
python -m pytest tests/test_data_engine.py -v

# Apenas testes do database
python -m pytest tests/test_database.py -v

# Apenas testes de fórmulas
python -m pytest tests/test_pricing_formulas.py -v
```

### Executar com cobertura

```bash
pip install pytest-cov
python -m pytest tests/ --cov=modules --cov-report=html
```

## Dependências de Teste

Os testes usam apenas a biblioteca padrão `unittest` do Python. Para cobertura, instale:

```bash
pip install pytest pytest-cov
```

## Cobertura Atual

Os testes cobrem:
- ✅ Validação de dados
- ✅ Métricas de qualidade
- ✅ Métricas de confiança
- ✅ Análise de sensibilidade
- ✅ Cálculo de buildup
- ✅ Validação de e-mail
- ✅ Validação de dados de usuário
- ✅ Sanitização de chaves privadas
- ✅ Fórmulas de precificação

## Notas

- Alguns testes podem requerer conexão com Firestore (testes de integração)
- Testes de validação criptográfica requerem biblioteca `cryptography` (opcional)
- Testes mockam `get_market_data()` quando necessário para evitar dependências externas

