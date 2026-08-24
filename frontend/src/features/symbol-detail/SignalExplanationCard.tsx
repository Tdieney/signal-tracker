import React from 'react';
import { Info } from 'lucide-react';
import { formatDateVi, formatPrice } from '../../lib/formatters';
import { SymbolExplanation } from '../../schemas/symbolSchema';

interface SignalExplanationCardProps {
  symbol: string;
  asOfDate: string;
  explanation: SymbolExplanation;
  signal?: string | null;
}

export const SignalExplanationCard: React.FC<SignalExplanationCardProps> = ({
  symbol,
  asOfDate,
  explanation,
}) => {
  const dateFormatted = formatDateVi(asOfDate);
  const curCloseStr = formatPrice(explanation.current_close);
  const curMa10Str = formatPrice(explanation.current_ma10);
  const prevCloseStr = formatPrice(explanation.previous_close);
  const prevMa10Str = formatPrice(explanation.previous_ma10);

  let explanationSentence = '';

  if (explanation.rule === 'CROSS_UP_MA10') {
    explanationSentence = `${symbol} được đánh dấu “Vừa cắt lên MA10” vì Close phiên ${dateFormatted} là ${curCloseStr}, cao hơn MA10 (${curMa10Str}); ở phiên hợp lệ trước đó Close (${prevCloseStr}) không cao hơn MA10 (${prevMa10Str}).`;
  } else if (explanation.rule === 'CROSS_DOWN_MA10') {
    explanationSentence = `${symbol} được đánh dấu “Vừa cắt xuống MA10” vì Close phiên ${dateFormatted} là ${curCloseStr}, thấp hơn MA10 (${curMa10Str}); ở phiên hợp lệ trước đó Close (${prevCloseStr}) không thấp hơn MA10 (${prevMa10Str}).`;
  } else if (explanation.rule === 'ABOVE_MA10') {
    explanationSentence = `${symbol} được đánh dấu “Trên MA10” vì Close phiên ${dateFormatted} là ${curCloseStr}, cao hơn MA10 (${curMa10Str}) và duy trì vị thế từ phiên trước.`;
  } else if (explanation.rule === 'BELOW_MA10') {
    explanationSentence = `${symbol} được đánh dấu “Dưới MA10” vì Close phiên ${dateFormatted} là ${curCloseStr}, thấp hơn MA10 (${curMa10Str}) và duy trì vị thế từ phiên trước.`;
  } else if (explanation.rule === 'ON_MA10') {
    explanationSentence = `Giá đóng cửa phiên ${dateFormatted} của ${symbol} (${curCloseStr}) bằng chính xác giá trị MA10 (${curMa10Str}).`;
  } else {
    explanationSentence = `${symbol} chưa có tín hiệu xác nhận ở phiên ${dateFormatted} do chưa đủ lịch sử tính toán 10 phiên giao dịch hợp lệ.`;
  }

  return (
    <div
      className="card"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderLeft: '4px solid var(--color-primary)',
        padding: 'var(--space-4)',
        marginBottom: 'var(--space-5)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', marginBottom: 'var(--space-2)' }}>
        <Info size={18} color="var(--color-primary)" aria-hidden="true" />
        <h3 className="text-h3" style={{ fontSize: '1rem' }}>Vì sao có tín hiệu này?</h3>
      </div>
      <p className="text-body" style={{ color: 'var(--color-text)', lineHeight: 1.6 }}>
        {explanationSentence}
      </p>
    </div>
  );
};
