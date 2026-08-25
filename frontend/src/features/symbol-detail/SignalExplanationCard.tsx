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
  const curMA10Str = formatPrice(explanation.current_ma10);
  const prevCloseStr = formatPrice(explanation.previous_close);
  const prevMA10Str = formatPrice(explanation.previous_ma10);

  let sentence = '';
  switch (explanation.rule) {
    case 'CROSS_UP_MA10':
      sentence = `Tại phiên ${dateFormatted}, giá đóng cửa của ${symbol} (${curCloseStr}) đã vượt lên trên đường MA10 (${curMA10Str}), sau khi phiên liền trước (${prevCloseStr}) nằm ở mức thấp hơn hoặc bằng MA10 (${prevMA10Str}).`;
      break;
    case 'CROSS_DOWN_MA10':
      sentence = `Tại phiên ${dateFormatted}, giá đóng cửa của ${symbol} (${curCloseStr}) đã cắt xuống dưới đường MA10 (${curMA10Str}), sau khi phiên liền trước (${prevCloseStr}) nằm ở mức cao hơn hoặc bằng MA10 (${prevMA10Str}).`;
      break;
    case 'ABOVE_MA10':
      sentence = `Tại phiên ${dateFormatted}, giá đóng cửa của ${symbol} (${curCloseStr}) tiếp tục duy trì ở phía trên đường MA10 (${curMA10Str}).`;
      break;
    case 'BELOW_MA10':
      sentence = `Tại phiên ${dateFormatted}, giá đóng cửa của ${symbol} (${curCloseStr}) tiếp tục nằm ở phía dưới đường MA10 (${curMA10Str}).`;
      break;
    case 'ON_MA10':
      sentence = `Tại phiên ${dateFormatted}, giá đóng cửa của ${symbol} (${curCloseStr}) bằng chính xác giá trị đường MA10 (${curMA10Str}).`;
      break;
    default:
      sentence = `Chưa đủ dữ liệu lịch sử để phân loại tín hiệu MA10 cho mã ${symbol}.`;
  }

  return (
    <div className="card explanation-card">
      <div className="explanation-header">
        <Info size={18} className="text-muted" aria-hidden="true" />
        <h2 className="text-h3">
          Giải thích tín hiệu kỹ thuật
        </h2>
      </div>
      <p className="text-body font-semibold">
        {sentence}
      </p>
      <p className="text-xs text-muted mt-2">
        Quy tắc: So sánh giá đóng cửa với giá trị trung bình 10 phiên giao dịch gần nhất (MA10).
      </p>
    </div>
  );
};
