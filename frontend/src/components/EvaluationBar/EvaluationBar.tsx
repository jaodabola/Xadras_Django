import React from 'react';
import './EvaluationBar.css';
import { StockfishEvaluation } from '../../hooks/useStockfish';

interface EvaluationBarProps {
  evaluation: StockfishEvaluation | null;
  orientation?: 'white' | 'black';
}

const EvaluationBar: React.FC<EvaluationBarProps> = ({ evaluation }) => {
  // A barra vai de -10 (Vantagem Preta) a +10 (Vantagem Branca)
  // 0 é o centro geométrico (50%)
  const MAX_CAP = 10.0;
  
  let fillPercentage = 50; // default (equal)
  let textLabel = '0.0';

  if (evaluation) {
    if (evaluation.mate !== null) {
      if (evaluation.mate > 0) {
        fillPercentage = 100; // Brancas ganham
        textLabel = `M${evaluation.mate}`;
      } else {
        fillPercentage = 0;   // Pretas ganham
        textLabel = `M${Math.abs(evaluation.mate)}`;
      }
    } else {
      // Usar uma fórmula não linear se quisermos amolecer notas altas,
      // Mas por agora, linear entre -10 e +10 com clamp.
      let score = evaluation.score;
      if (score > MAX_CAP) score = MAX_CAP;
      if (score < -MAX_CAP) score = -MAX_CAP;
      
      fillPercentage = 50 + (score / MAX_CAP) * 50;
      textLabel = (evaluation.score > 0 ? '+' : '') + evaluation.score.toFixed(1);
    }
  }

  const isTop = evaluation?.score ? evaluation.score < 0 : false;
  
  return (
    <div className="evaluation-bar">
      <div className="evaluation-bar-black"></div>
      <div 
        className="evaluation-bar-white" 
        style={{ height: `${fillPercentage}%` }}
      ></div>
      <div className={`evaluation-text ${isTop ? 'top' : 'bottom'}`}>
        {evaluation ? textLabel : '0.0'}
      </div>
    </div>
  );
};

export default EvaluationBar;
