"""
Pacote de avaliação contínua de respostas de LLMs.
Contém métricas para verificação de groundedness, relevância de respostas e taxa de alucinação.
"""

from src.eval.evaluator import EvalResult, Evaluator, get_evaluator

__all__ = ["Evaluator", "EvalResult", "get_evaluator"]